export interface ProjectSession {
  threadId: string;
  projectName: string;
  createdAt: string;
  updatedAt?: string;
  root?: string;
}

const projectSessionStorageKey = "writeagent_project_session";

export interface ProjectSessionApiRecord {
  project_id?: unknown;
  project_name?: unknown;
  projectName?: unknown;
  thread_id?: unknown;
  threadId?: unknown;
  created_at?: unknown;
  createdAt?: unknown;
  updated_at?: unknown;
  updatedAt?: unknown;
  root?: unknown;
}

interface CreateProjectSessionOptions {
  now?: Date;
  randomUUID?: () => string;
}

interface ProjectSessionActivity {
  liveMessageCount?: number;
  persistedMessageCount?: number;
  isRunning?: boolean;
  knownSession?: boolean;
}

export function createProjectSession(options: CreateProjectSessionOptions = {}): ProjectSession {
  const now = options.now ?? new Date();
  const randomUUID = options.randomUUID ?? defaultRandomUUID;
  const threadId = normalizeThreadId(randomUUID()) ?? defaultRandomUUID();
  const createdAt = now.toISOString();
  return {
    threadId,
    projectName: projectNameForThread(formatLocalTimestamp(now), threadId),
    createdAt,
    updatedAt: createdAt,
  };
}

export function ensureProjectSession(storage: Storage | null = browserSessionStorage()): ProjectSession {
  const existing = loadProjectSession(storage);
  if (existing) {
    saveProjectSession(existing, storage);
    return existing;
  }
  const created = createProjectSession();
  saveProjectSession(created, storage);
  return created;
}

export function loadProjectSession(storage: Storage | null = browserSessionStorage()): ProjectSession | null {
  if (!storage) {
    return null;
  }
  try {
    const raw = storage.getItem(projectSessionStorageKey);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<ProjectSession>;
    if (!parsed.threadId || !parsed.projectName || !parsed.createdAt) {
      return null;
    }
    const threadId = normalizeThreadId(parsed.threadId);
    if (!threadId) {
      return null;
    }
    return {
      threadId,
      projectName: sanitizeProjectName(parsed.projectName),
      createdAt: String(parsed.createdAt),
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : undefined,
      root: typeof parsed.root === "string" ? parsed.root : undefined,
    };
  } catch {
    return null;
  }
}

export function saveProjectSession(session: ProjectSession, storage: Storage | null = browserSessionStorage()): void {
  storage?.setItem(projectSessionStorageKey, JSON.stringify(session));
}

export function clearProjectSession(storage: Storage | null = browserSessionStorage()): void {
  storage?.removeItem(projectSessionStorageKey);
}

export function artifactRootForProject(projectName: string): string {
  return `.writeagent/projects/${sanitizeProjectName(projectName)}/artifacts`;
}

export function projectRootForProject(projectName: string): string {
  return `.writeagent/projects/${sanitizeProjectName(projectName)}`;
}

export function projectQuery(projectName: string): string {
  return `project_id=${encodeURIComponent(sanitizeProjectName(projectName))}`;
}

export function projectSessionFromApi(raw: unknown): ProjectSession | null {
  const value = recordValue(raw);
  if (!value) {
    return null;
  }

  const projectName = stringValue(value.project_id) ?? stringValue(value.project_name) ?? stringValue(value.projectName);
  if (!projectName) {
    return null;
  }

  const threadId = normalizeThreadId(stringValue(value.thread_id) ?? stringValue(value.threadId) ?? projectName);
  if (!threadId) {
    return null;
  }

  const createdAt = stringValue(value.created_at) ?? stringValue(value.createdAt) ?? new Date(0).toISOString();
  const updatedAt = stringValue(value.updated_at) ?? stringValue(value.updatedAt) ?? createdAt;
  return {
    threadId,
    projectName: sanitizeProjectName(projectName),
    createdAt,
    updatedAt,
    root: stringValue(value.root) ?? undefined,
  };
}

export function sortProjectSessions(sessions: Array<ProjectSession | null | undefined>): ProjectSession[] {
  return sessions
    .filter((session): session is ProjectSession => Boolean(session))
    .sort((left, right) => {
      const timeDelta = sessionTimestamp(right) - sessionTimestamp(left);
      if (timeDelta !== 0) {
        return timeDelta;
      }
      return right.projectName.localeCompare(left.projectName);
    });
}

export function shouldActivateProjectSession(activity: ProjectSessionActivity): boolean {
  return Boolean(
    activity.isRunning ||
      (activity.liveMessageCount ?? 0) > 0 ||
      (activity.persistedMessageCount ?? 0) > 0 ||
      activity.knownSession,
  );
}

export function sessionDisplayLabel(session: ProjectSession): string {
  const projectTimestamp = projectTimestampLabel(session.projectName);
  if (projectTimestamp) {
    return `${projectTimestamp} · ${session.threadId.slice(0, 8)}`;
  }

  const timestamp = Date.parse(session.createdAt);
  const date = Number.isFinite(timestamp) ? new Date(timestamp) : null;
  const dateLabel = date
    ? `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
    : session.projectName.split("_")[0] || "session";
  return `${dateLabel} · ${session.threadId.slice(0, 8)}`;
}

function formatLocalTimestamp(date: Date): string {
  return [
    date.getFullYear(),
    pad2(date.getMonth() + 1),
    pad2(date.getDate()),
    "-",
    pad2(date.getHours()),
    pad2(date.getMinutes()),
    pad2(date.getSeconds()),
  ].join("");
}

export function projectNameForThread(timestamp: string, threadId: string): string {
  return `${sanitizeProjectName(timestamp)}_thread-${sanitizeProjectName(threadId)}`;
}

export function normalizeThreadId(value: string): string | null {
  const sanitized = sanitizeProjectName(value);
  const projectThreadMatch = sanitized.match(/(?:^|_)thread-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i);
  const candidate = projectThreadMatch?.[1] ?? (sanitized.startsWith("thread-") ? sanitized.slice("thread-".length) : sanitized);
  return isUuid(candidate) ? candidate : null;
}

function sanitizeProjectName(value: string): string {
  const cleaned = String(value)
    .replace(/[\\/]+/g, "-")
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^[._-]+|[._-]+$/g, "");
  return cleaned || "default";
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function sessionTimestamp(session: ProjectSession): number {
  const timestamp = Date.parse(session.updatedAt ?? session.createdAt);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function projectTimestampLabel(projectName: string): string | null {
  const match = sanitizeProjectName(projectName).match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})(?:_|$)/);
  if (!match) {
    return null;
  }
  const [, year, month, day, hour, minute] = match;
  return `${year}-${month}-${day} ${hour}:${minute}`;
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function defaultRandomUUID(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const hex = (length: number) =>
    Array.from({ length }, () => Math.floor(Math.random() * 16).toString(16)).join("");
  const variant = (8 + Math.floor(Math.random() * 4)).toString(16);
  return `${hex(8)}-${hex(4)}-4${hex(3)}-${variant}${hex(3)}-${hex(12)}`;
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function browserSessionStorage(): Storage | null {
  try {
    return typeof sessionStorage === "undefined" ? null : sessionStorage;
  } catch {
    return null;
  }
}

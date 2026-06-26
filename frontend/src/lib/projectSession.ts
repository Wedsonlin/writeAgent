export interface ProjectSession {
  threadId: string;
  projectName: string;
  createdAt: string;
}

const projectSessionStorageKey = "writeagent_project_session";

interface CreateProjectSessionOptions {
  now?: Date;
  randomUUID?: () => string;
}

export function createProjectSession(options: CreateProjectSessionOptions = {}): ProjectSession {
  const now = options.now ?? new Date();
  const randomUUID = options.randomUUID ?? defaultRandomUUID;
  const threadId = normalizeThreadId(randomUUID()) ?? defaultRandomUUID();
  return {
    threadId,
    projectName: projectNameForThread(formatLocalTimestamp(now), threadId),
    createdAt: now.toISOString(),
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

function formatLocalTimestamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    "-",
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
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

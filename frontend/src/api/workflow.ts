import type { WorkflowMeta, WorkflowProgressPayload } from "../types/workflow";
const viteEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env;
export const agentUrl = viteEnv?.VITE_AGENT_URL ?? "http://localhost:2024";

export interface ProjectSessionApiRecord {
  project_id?: unknown;
  project_name?: unknown;
  thread_id?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  root?: unknown;
}

interface ProjectSessionRequest {
  projectName: string;
  threadId: string;
  createdAt: string;
  updatedAt?: string;
}

export interface ProjectSessionMessagesRecord {
  project_id?: unknown;
  messages?: unknown;
  updated_at?: unknown;
}

export async function fetchWorkflowMeta(): Promise<WorkflowMeta> {
  const response = await fetch(`${agentUrl}/api/workflow/meta`);
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow meta: ${response.status}`);
  }
  return response.json();
}

export async function fetchWorkflowProgress(projectId?: string | null): Promise<WorkflowProgressPayload> {
  const response = await fetch(workflowProgressUrl(projectId));
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow progress: ${response.status}`);
  }
  return response.json();
}

export async function fetchCaseRequirement(): Promise<{ path: string; content: string }> {
  const response = await fetch(`${agentUrl}/api/case/original-requirement`);
  if (!response.ok) {
    throw new Error(`Failed to fetch case requirement: ${response.status}`);
  }
  return response.json();
}

export async function fetchProjectSessions(): Promise<ProjectSessionApiRecord[]> {
  const response = await fetch(projectSessionsUrl());
  if (!response.ok) {
    throw new Error(`Failed to fetch project sessions: ${response.status}`);
  }
  const payload = await response.json() as { sessions?: ProjectSessionApiRecord[] };
  return payload.sessions ?? [];
}

export async function registerProjectSession(session: ProjectSessionRequest): Promise<ProjectSessionApiRecord> {
  const response = await fetch(projectSessionsUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: session.projectName,
      thread_id: session.threadId,
      created_at: session.createdAt,
      updated_at: session.updatedAt,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to save project session: ${response.status}`);
  }
  return response.json();
}

export function projectSessionsUrl(): string {
  return new URL(`${agentUrl}/api/sessions`).toString();
}

export async function fetchProjectSessionMessages(projectId: string): Promise<unknown[]> {
  const response = await fetch(projectSessionMessagesUrl(projectId));
  if (!response.ok) {
    throw new Error(`Failed to fetch project session messages: ${response.status}`);
  }
  const payload = await response.json() as ProjectSessionMessagesRecord;
  return Array.isArray(payload.messages) ? payload.messages : [];
}

export async function saveProjectSessionMessages(projectId: string, messages: unknown[]): Promise<void> {
  const response = await fetch(projectSessionMessagesUrl(projectId), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!response.ok) {
    throw new Error(`Failed to save project session messages: ${response.status}`);
  }
}

export function projectSessionMessagesUrl(projectId: string): string {
  return new URL(`${agentUrl}/api/sessions/${encodeURIComponent(projectId)}/messages`).toString();
}

export function workflowProgressUrl(projectId?: string | null): string {
  const url = new URL(`${agentUrl}/api/workflow/progress`);
  if (projectId) {
    url.searchParams.set("project_id", projectId);
  }
  return url.toString();
}

export function artifactFileUrl(
  artifactId: string,
  kind: "json" | "markdown" | "docx" | "pdf",
  projectId?: string | null,
): string {
  const url = new URL(`${agentUrl}/api/artifacts/${encodeURIComponent(artifactId)}/files/${kind}`);
  if (projectId) {
    url.searchParams.set("project_id", projectId);
  }
  return url.toString();
}

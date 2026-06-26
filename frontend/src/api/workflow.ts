import type { WorkflowMeta, WorkflowProgressPayload } from "../types/workflow";

const viteEnv = (import.meta as unknown as { env?: Record<string, string | undefined> }).env;
export const agentUrl = viteEnv?.VITE_AGENT_URL ?? "http://localhost:2024";

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

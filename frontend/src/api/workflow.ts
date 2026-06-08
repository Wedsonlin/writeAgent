import type { WorkflowMeta, WorkflowProgressPayload } from "../types/workflow";

export const agentUrl = import.meta.env.VITE_AGENT_URL ?? "http://localhost:2024";

export async function fetchWorkflowMeta(): Promise<WorkflowMeta> {
  const response = await fetch(`${agentUrl}/api/workflow/meta`);
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow meta: ${response.status}`);
  }
  return response.json();
}

export async function fetchWorkflowProgress(): Promise<WorkflowProgressPayload> {
  const response = await fetch(`${agentUrl}/api/workflow/progress`);
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow progress: ${response.status}`);
  }
  return response.json();
}

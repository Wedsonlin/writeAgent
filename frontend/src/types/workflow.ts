export type StageStatus = "pending" | "in_progress" | "completed" | "blocked" | "failed";

export interface WorkflowStageMeta {
  id: string;
  title: string;
  skill: string;
  requires: string[];
  produces: string[];
  description: string;
  quality_checks: string[];
}

export interface WorkflowMeta {
  workflow_id: string;
  title: string;
  stages: WorkflowStageMeta[];
}

export interface StageProgress {
  stage_id: string;
  status: StageStatus;
  input_artifacts: string[];
  output_artifacts: string[];
  blocked_reason?: string | null;
  updated_at: string;
}

export interface ArtifactMeta {
  artifact_id: string;
  artifact_type: string;
  schema_name?: string | null;
  path: string;
  summary?: string | null;
  stage_id?: string | null;
  metadata?: Record<string, unknown>;
  version: number;
}

export interface WorkflowProgressPayload {
  workflow_id: string;
  project_id?: string;
  current_stage?: string | null;
  blocked_reason?: string | null;
  updated_at: string;
  stages: StageProgress[];
  artifacts: ArtifactMeta[];
}

import type { WorkflowMeta, WorkflowProgressPayload, StageStatus } from "../types/workflow";

const stageLabels: Record<string, string> = {
  requirement_analysis: "需求分析",
  literature_review: "文献梳理",
  paper_outline: "大纲撰写",
  content_generation: "正文生成",
  academic_formatting: "学术格式",
  polish_and_plagiarism: "润色查重",
};

const statusLabels: Record<StageStatus, string> = {
  pending: "待处理",
  in_progress: "进行中",
  completed: "已完成",
  blocked: "阻塞",
  failed: "失败",
};

interface Props {
  meta: WorkflowMeta | null;
  progress: WorkflowProgressPayload | null;
  error?: string | null;
}

export function WorkflowProgress({ meta, progress, error }: Props) {
  const stages = meta?.stages ?? [];
  const progressByStage = new Map((progress?.stages ?? []).map((stage) => [stage.stage_id, stage]));
  const artifactCount = progress?.artifacts.length ?? 0;

  return (
    <section className="workflow-panel">
      <div className="panel-header">
        <div>
          <h2>论文写作工作流</h2>
          <p>{meta?.title ?? "Academic Paper Writing Workflow"}</p>
        </div>
        {progress?.current_stage && (
          <span className="current-stage">当前：{labelFor(progress.current_stage)}</span>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="stage-row">
        {stages.map((stage, index) => {
          const stageProgress = progressByStage.get(stage.id);
          const status = stageProgress?.status ?? "pending";
          return (
            <div className="stage-item" key={stage.id} style={{ animationDelay: `${index * 60}ms` }}>
              <div className={`stage-pill ${status}`}>
                <span className="stage-number">
                  {status === "completed" ? "\u2713" : index + 1}
                </span>
                <span className="stage-label">{labelFor(stage.id)}</span>
                <span className="stage-status">{statusLabels[status]}</span>
              </div>
              {index < stages.length - 1 && (
                <div className={`stage-line ${status === "completed" ? "completed" : ""}`} />
              )}
            </div>
          );
        })}
      </div>

      <div className="artifact-badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        产出文档 <span className="count">{artifactCount}</span>
      </div>
    </section>
  );
}

function labelFor(stageId: string): string {
  return stageLabels[stageId] ?? stageId;
}

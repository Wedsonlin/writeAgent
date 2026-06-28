import { useCallback, useEffect, useState } from "react";
import { fetchWorkflowMeta, fetchWorkflowProgress } from "../api/workflow";
import type { WorkflowMeta, WorkflowProgressPayload } from "../types/workflow";

export function useWorkflowProgress(isLoading: boolean, projectId?: string | null) {
  const [meta, setMeta] = useState<WorkflowMeta | null>(null);
  const [progress, setProgress] = useState<WorkflowProgressPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const nextMeta = await fetchWorkflowMeta();
      const nextProgress = projectId ? await fetchWorkflowProgress(projectId) : null;
      setMeta(nextMeta);
      setProgress(nextProgress);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refresh();
    }, isLoading ? 1500 : 3000);
    return () => window.clearInterval(interval);
  }, [isLoading, refresh]);

  return { meta, progress, error, refresh };
}

import { useEffect, useState } from "react";
import { extractPendingInterrupts, threadStateUrl, type PendingInterrupt } from "../lib/threadInterrupts";

const POLL_INTERVAL_MS = 2000;

export function useThreadInterrupts(apiUrl: string, threadId: string | undefined, enabled: boolean): PendingInterrupt[] {
  const [interrupts, setInterrupts] = useState<PendingInterrupt[]>([]);

  useEffect(() => {
    if (!enabled || !threadId) {
      setInterrupts([]);
      return;
    }

    let cancelled = false;
    const currentThreadId = threadId;

    async function loadInterrupts() {
      try {
        const response = await fetch(threadStateUrl(apiUrl, currentThreadId));
        if (!response.ok) {
          throw new Error(`Failed to fetch thread state: ${response.status}`);
        }
        const state = await response.json() as unknown;
        if (!cancelled) {
          setInterrupts(extractPendingInterrupts(state));
        }
      } catch (error) {
        if (!cancelled) {
          console.warn("writeAgent thread interrupt fallback failed", error);
          setInterrupts([]);
        }
      }
    }

    void loadInterrupts();
    const interval = window.setInterval(() => void loadInterrupts(), POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [apiUrl, threadId, enabled]);

  return interrupts;
}

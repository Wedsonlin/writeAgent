interface TerminationVisibility {
  isRunning: boolean;
  isTerminating: boolean;
}

interface StoppableStream {
  stop?: (options?: { cancel?: boolean }) => Promise<unknown> | unknown;
}

export function shouldShowTerminateGeneration(state: TerminationVisibility): boolean {
  return state.isRunning || state.isTerminating;
}

export async function terminateGeneration(stream: StoppableStream): Promise<void> {
  if (!stream || typeof stream.stop !== "function") {
    throw new Error("Current stream does not support termination.");
  }
  await stream.stop({ cancel: true });
}

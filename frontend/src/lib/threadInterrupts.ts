export interface PendingInterrupt extends Record<string, unknown> {
  id?: string;
  interruptId?: string;
  interrupt_id?: string;
  namespace?: string[];
}

export function threadStateUrl(apiUrl: string, threadId: string): string {
  return new URL(`/threads/${encodeURIComponent(threadId)}/state`, apiUrl).toString();
}

export function extractPendingInterrupts(state: unknown): PendingInterrupt[] {
  const pending: PendingInterrupt[] = [];
  const value = recordValue(state);
  if (!value) {
    return pending;
  }

  collectInterrupts(value.interrupts, pending);

  const tasks = Array.isArray(value.tasks) ? value.tasks : [];
  for (const task of tasks) {
    const taskRecord = recordValue(task);
    if (!taskRecord) {
      continue;
    }
    collectInterrupts(taskRecord.interrupts, pending);
  }

  return uniqueInterrupts(pending);
}

export function extractThreadStreamInterrupts(thread: unknown): PendingInterrupt[] {
  const value = recordValue(thread);
  if (!value) {
    return [];
  }
  const pending: PendingInterrupt[] = [];
  collectThreadStreamInterrupts(value.interrupts, pending);
  return uniqueInterrupts(pending);
}

export function mergeInterrupts(root: unknown[] | undefined, fallback: unknown[] | undefined): PendingInterrupt[] {
  const merged: PendingInterrupt[] = [];
  collectInterrupts(root, merged);
  collectInterrupts(fallback, merged);
  return uniqueInterrupts(merged);
}

function collectInterrupts(raw: unknown, target: PendingInterrupt[]) {
  if (Array.isArray(raw)) {
    for (const item of raw) {
      const interrupt = pendingInterrupt(item);
      if (interrupt) {
        target.push(interrupt);
      }
    }
    return;
  }

  const record = recordValue(raw);
  if (!record) {
    return;
  }

  for (const value of Object.values(record)) {
    if (Array.isArray(value)) {
      collectInterrupts(value, target);
    } else {
      const interrupt = pendingInterrupt(value);
      if (interrupt) {
        target.push(interrupt);
      }
    }
  }
}

function collectThreadStreamInterrupts(raw: unknown, target: PendingInterrupt[]) {
  if (Array.isArray(raw)) {
    for (const item of raw) {
      const interrupt = threadStreamInterrupt(item);
      if (interrupt) {
        target.push(interrupt);
      }
    }
    return;
  }

  const record = recordValue(raw);
  if (!record) {
    return;
  }

  for (const value of Object.values(record)) {
    collectThreadStreamInterrupts(value, target);
  }
}

function pendingInterrupt(raw: unknown): PendingInterrupt | null {
  const record = recordValue(raw);
  if (!record) {
    return null;
  }
  const interrupt: PendingInterrupt = { ...record };
  if (Array.isArray(interrupt.namespace)) {
    interrupt.namespace = interrupt.namespace.map(String);
  }
  return interrupt;
}

function threadStreamInterrupt(raw: unknown): PendingInterrupt | null {
  const record = recordValue(raw);
  if (!record) {
    return null;
  }
  const interruptId = stringValue(record.interruptId) ?? stringValue(record.id) ?? stringValue(record.interrupt_id);
  if (!interruptId) {
    return pendingInterrupt(raw);
  }
  const interrupt: PendingInterrupt = {
    ...record,
    id: stringValue(record.id) ?? interruptId,
    interruptId,
    value: "payload" in record ? record.payload : record.value,
  };
  if (Array.isArray(record.namespace)) {
    interrupt.namespace = record.namespace.map(String);
  }
  return interrupt;
}

function uniqueInterrupts(interrupts: PendingInterrupt[]): PendingInterrupt[] {
  const seen = new Set<string>();
  const unique: PendingInterrupt[] = [];
  for (const interrupt of interrupts) {
    const key = interruptKey(interrupt);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(interrupt);
  }
  return unique;
}

function interruptKey(interrupt: PendingInterrupt): string {
  return stringValue(interrupt.id)
    ?? stringValue(interrupt.interruptId)
    ?? stringValue(interrupt.interrupt_id)
    ?? JSON.stringify(interrupt);
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? value as Record<string, unknown> : null;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

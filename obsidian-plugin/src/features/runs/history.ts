let lastRunId: string | null = null;

export function setLastRunId(runId: unknown): void {
  if (typeof runId !== "string") {
    lastRunId = null;
    return;
  }

  const value = runId.trim();
  lastRunId = value.length > 0 ? value : null;
}

export function getLastRunId(): string | null {
  return lastRunId;
}

export function clearLastRunId(): void {
  lastRunId = null;
}

let lastRunId: string | null = null;

export function setLastRunId(runId: string): void {
  const value = runId.trim();
  lastRunId = value.length > 0 ? value : null;
}

export function getLastRunId(): string | null {
  return lastRunId;
}

export function clearLastRunId(): void {
  lastRunId = null;
}

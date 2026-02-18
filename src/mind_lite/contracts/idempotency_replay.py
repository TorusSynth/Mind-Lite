from dataclasses import dataclass


@dataclass(frozen=True)
class ApplyEventResult:
    accepted: bool
    duplicate: bool
    reason: str


class RunReplayLedger:
    def __init__(self) -> None:
        self._events_by_run: dict[str, list[str]] = {}
        self._seen_by_run: dict[str, set[str]] = {}

    def replay_order(self, run_id: str) -> list[str]:
        return list(self._events_by_run.get(run_id, []))


def apply_event(ledger: RunReplayLedger, run_id: str, event_id: str) -> ApplyEventResult:
    seen = ledger._seen_by_run.setdefault(run_id, set())
    if event_id in seen:
        return ApplyEventResult(accepted=False, duplicate=True, reason="duplicate_event_id")

    seen.add(event_id)
    ledger._events_by_run.setdefault(run_id, []).append(event_id)
    return ApplyEventResult(accepted=True, duplicate=False, reason="accepted")

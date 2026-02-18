from dataclasses import dataclass

from mind_lite.contracts.snapshot_rollback import SnapshotStore


@dataclass(frozen=True)
class RollbackDecision:
    allowed: bool
    reason: str


def validate_rollback_request(store: SnapshotStore, run_id: str, snapshot_id: str) -> RollbackDecision:
    records = store._records_by_run.get(run_id, [])
    if not records:
        return RollbackDecision(allowed=False, reason="snapshot_not_found")

    matching = [record for record in records if record.snapshot_id == snapshot_id]
    if not matching:
        return RollbackDecision(allowed=False, reason="snapshot_not_found")

    latest = records[-1]
    if latest.snapshot_id != snapshot_id:
        return RollbackDecision(allowed=False, reason="not_latest_snapshot")

    return RollbackDecision(allowed=True, reason="allowed")

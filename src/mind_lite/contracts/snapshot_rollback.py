from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotRecord:
    snapshot_id: str
    run_id: str
    changed_note_ids: list[str]


class SnapshotStore:
    def __init__(self) -> None:
        self._records_by_run: dict[str, list[SnapshotRecord]] = {}

    def add(self, record: SnapshotRecord) -> None:
        self._records_by_run.setdefault(record.run_id, []).append(record)

    def latest_for_run(self, run_id: str) -> SnapshotRecord:
        records = self._records_by_run.get(run_id, [])
        if not records:
            raise ValueError(f"no snapshots recorded for run: {run_id}")
        return records[-1]


def apply_batch(store: SnapshotStore, run_id: str, changed_note_ids: list[str]) -> SnapshotRecord:
    version = len(store._records_by_run.get(run_id, [])) + 1
    record = SnapshotRecord(
        snapshot_id=f"snap-{run_id}-{version}",
        run_id=run_id,
        changed_note_ids=list(changed_note_ids),
    )
    store.add(record)
    return record

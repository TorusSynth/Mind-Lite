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

    def export_records(self) -> dict[str, list[dict]]:
        exported: dict[str, list[dict]] = {}
        for run_id, records in self._records_by_run.items():
            exported[run_id] = [
                {
                    "snapshot_id": record.snapshot_id,
                    "run_id": record.run_id,
                    "changed_note_ids": list(record.changed_note_ids),
                }
                for record in records
            ]
        return exported

    def import_records(self, payload: dict[str, list[dict]]) -> None:
        restored: dict[str, list[SnapshotRecord]] = {}
        for run_id, records in payload.items():
            restored[run_id] = [
                SnapshotRecord(
                    snapshot_id=item["snapshot_id"],
                    run_id=item["run_id"],
                    changed_note_ids=list(item.get("changed_note_ids", [])),
                )
                for item in records
            ]
        self._records_by_run = restored


def apply_batch(store: SnapshotStore, run_id: str, changed_note_ids: list[str]) -> SnapshotRecord:
    version = len(store._records_by_run.get(run_id, [])) + 1
    record = SnapshotRecord(
        snapshot_id=f"snap-{run_id}-{version}",
        run_id=run_id,
        changed_note_ids=list(changed_note_ids),
    )
    store.add(record)
    return record

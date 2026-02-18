import unittest

from mind_lite.contracts.snapshot_rollback import SnapshotStore, apply_batch


class SnapshotRollbackPolicyTests(unittest.TestCase):
    def test_apply_batch_creates_snapshot_record(self):
        store = SnapshotStore()
        changed_notes = ["note-1", "note-2"]

        record = apply_batch(store=store, run_id="run-001", changed_note_ids=changed_notes)

        self.assertEqual(record.run_id, "run-001")
        self.assertEqual(record.changed_note_ids, changed_notes)
        self.assertTrue(record.snapshot_id.startswith("snap-run-001-"))

    def test_store_returns_latest_snapshot_for_run(self):
        store = SnapshotStore()

        first = apply_batch(store=store, run_id="run-001", changed_note_ids=["note-1"])
        second = apply_batch(store=store, run_id="run-001", changed_note_ids=["note-2"])

        latest = store.latest_for_run("run-001")
        self.assertEqual(latest.snapshot_id, second.snapshot_id)
        self.assertNotEqual(latest.snapshot_id, first.snapshot_id)

    def test_latest_for_run_raises_when_missing(self):
        store = SnapshotStore()
        with self.assertRaises(ValueError):
            store.latest_for_run("missing-run")


if __name__ == "__main__":
    unittest.main()

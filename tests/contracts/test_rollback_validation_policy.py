import unittest

from mind_lite.contracts.rollback_validation import validate_rollback_request
from mind_lite.contracts.snapshot_rollback import SnapshotStore, apply_batch


class RollbackValidationPolicyTests(unittest.TestCase):
    def test_accepts_rollback_for_latest_snapshot_same_run(self):
        store = SnapshotStore()
        latest = apply_batch(store=store, run_id="run-1", changed_note_ids=["n1"])

        decision = validate_rollback_request(store=store, run_id="run-1", snapshot_id=latest.snapshot_id)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "allowed")

    def test_rejects_when_snapshot_missing(self):
        store = SnapshotStore()
        apply_batch(store=store, run_id="run-1", changed_note_ids=["n1"])

        decision = validate_rollback_request(store=store, run_id="run-1", snapshot_id="snap-run-1-99")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "snapshot_not_found")

    def test_rejects_when_snapshot_not_latest_for_run(self):
        store = SnapshotStore()
        first = apply_batch(store=store, run_id="run-1", changed_note_ids=["n1"])
        apply_batch(store=store, run_id="run-1", changed_note_ids=["n2"])

        decision = validate_rollback_request(store=store, run_id="run-1", snapshot_id=first.snapshot_id)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "not_latest_snapshot")


if __name__ == "__main__":
    unittest.main()

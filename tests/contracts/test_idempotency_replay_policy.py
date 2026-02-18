import unittest

from mind_lite.contracts.idempotency_replay import RunReplayLedger, apply_event


class IdempotencyReplayPolicyTests(unittest.TestCase):
    def test_accepts_first_event_id(self):
        ledger = RunReplayLedger()

        result = apply_event(ledger, run_id="run-1", event_id="evt-1")

        self.assertTrue(result.accepted)
        self.assertFalse(result.duplicate)

    def test_rejects_duplicate_event_id_within_same_run(self):
        ledger = RunReplayLedger()
        apply_event(ledger, run_id="run-1", event_id="evt-1")

        result = apply_event(ledger, run_id="run-1", event_id="evt-1")

        self.assertFalse(result.accepted)
        self.assertTrue(result.duplicate)
        self.assertEqual(result.reason, "duplicate_event_id")

    def test_allows_same_event_id_in_different_runs(self):
        ledger = RunReplayLedger()
        first = apply_event(ledger, run_id="run-1", event_id="evt-1")
        second = apply_event(ledger, run_id="run-2", event_id="evt-1")

        self.assertTrue(first.accepted)
        self.assertTrue(second.accepted)

    def test_replay_order_preserved_for_run(self):
        ledger = RunReplayLedger()
        apply_event(ledger, run_id="run-1", event_id="evt-1")
        apply_event(ledger, run_id="run-1", event_id="evt-2")

        self.assertEqual(ledger.replay_order("run-1"), ["evt-1", "evt-2"])


if __name__ == "__main__":
    unittest.main()

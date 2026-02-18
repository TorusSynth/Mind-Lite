import unittest

from mind_lite.contracts.run_lifecycle import (
    RunState,
    can_transition,
    validate_transition,
)


class RunLifecyclePolicyTests(unittest.TestCase):
    def test_allows_linear_forward_transition(self):
        self.assertTrue(can_transition(RunState.QUEUED, RunState.ANALYZING))
        self.assertTrue(validate_transition(RunState.ANALYZING, RunState.READY_SAFE_AUTO))

    def test_allows_analyzing_to_awaiting_review_without_auto_ready_hop(self):
        self.assertTrue(can_transition(RunState.ANALYZING, RunState.AWAITING_REVIEW))
        self.assertTrue(validate_transition(RunState.ANALYZING, RunState.AWAITING_REVIEW))

    def test_allows_review_to_approval_path(self):
        self.assertTrue(can_transition(RunState.AWAITING_REVIEW, RunState.APPROVED))
        self.assertTrue(validate_transition(RunState.APPROVED, RunState.APPLIED))
        self.assertTrue(validate_transition(RunState.APPLIED, RunState.VERIFIED))

    def test_allows_global_failure_state_entry(self):
        self.assertTrue(can_transition(RunState.QUEUED, RunState.AUTO_SAFE_MODE))
        self.assertTrue(can_transition(RunState.APPLIED, RunState.ROLLED_BACK))
        self.assertTrue(can_transition(RunState.ANALYZING, RunState.FAILED_NEEDS_ATTENTION))

    def test_rejects_invalid_transition(self):
        self.assertFalse(can_transition(RunState.QUEUED, RunState.APPLIED))
        self.assertFalse(validate_transition(RunState.QUEUED, RunState.APPLIED))

    def test_rejects_verified_to_previous_workflow_states(self):
        self.assertFalse(can_transition(RunState.VERIFIED, RunState.ANALYZING))
        self.assertFalse(validate_transition(RunState.VERIFIED, RunState.READY_SAFE_AUTO))


if __name__ == "__main__":
    unittest.main()

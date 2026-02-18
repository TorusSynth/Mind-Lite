import unittest

from mind_lite.contracts.action_tiering import ActionMode, decide_action_mode


class ActionTieringPolicyTests(unittest.TestCase):
    def test_low_risk_auto_at_threshold(self):
        self.assertEqual(decide_action_mode("low", 0.80), ActionMode.AUTO)

    def test_low_risk_manual_below_threshold(self):
        self.assertEqual(decide_action_mode("low", 0.79), ActionMode.MANUAL)

    def test_medium_risk_suggest_at_threshold(self):
        self.assertEqual(decide_action_mode("medium", 0.70), ActionMode.SUGGEST)

    def test_medium_risk_manual_below_threshold(self):
        self.assertEqual(decide_action_mode("medium", 0.69), ActionMode.MANUAL)

    def test_high_risk_always_manual(self):
        self.assertEqual(decide_action_mode("high", 0.99), ActionMode.MANUAL)

    def test_invalid_risk_tier_raises(self):
        with self.assertRaises(ValueError):
            decide_action_mode("unknown", 0.90)

    def test_out_of_range_confidence_raises(self):
        with self.assertRaises(ValueError):
            decide_action_mode("low", 1.01)


if __name__ == "__main__":
    unittest.main()

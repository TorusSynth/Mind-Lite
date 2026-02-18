import unittest

from mind_lite.contracts.budget_guardrails import BudgetDecision, evaluate_budget


class BudgetGuardrailsPolicyTests(unittest.TestCase):
    def test_returns_normal_below_70_percent(self):
        decision = evaluate_budget(monthly_spend=20.0, monthly_cap=30.0)
        self.assertEqual(decision.status, "normal")
        self.assertTrue(decision.cloud_allowed)

    def test_returns_warn_70_at_threshold(self):
        decision = evaluate_budget(monthly_spend=21.0, monthly_cap=30.0)
        self.assertEqual(decision.status, "warn_70")
        self.assertTrue(decision.cloud_allowed)

    def test_returns_warn_90_at_threshold(self):
        decision = evaluate_budget(monthly_spend=27.0, monthly_cap=30.0)
        self.assertEqual(decision.status, "warn_90")
        self.assertTrue(decision.cloud_allowed)

    def test_returns_hard_stop_at_cap(self):
        decision = evaluate_budget(monthly_spend=30.0, monthly_cap=30.0)
        self.assertEqual(decision.status, "hard_stop")
        self.assertFalse(decision.cloud_allowed)
        self.assertTrue(decision.local_only_mode)

    def test_rejects_negative_inputs(self):
        with self.assertRaises(ValueError):
            evaluate_budget(monthly_spend=-1.0, monthly_cap=30.0)

    def test_rejects_non_positive_cap(self):
        with self.assertRaises(ValueError):
            evaluate_budget(monthly_spend=1.0, monthly_cap=0.0)


if __name__ == "__main__":
    unittest.main()

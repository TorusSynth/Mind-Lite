import unittest

from mind_lite.contracts.provider_routing import RoutingInput, select_provider


class ProviderRoutingPolicyTests(unittest.TestCase):
    def test_defaults_to_local_when_no_triggers(self):
        decision = select_provider(
            RoutingInput(local_confidence=0.85, local_timed_out=False, grounding_failed=False)
        )
        self.assertEqual(decision.provider, "local")
        self.assertFalse(decision.fallback_used)

    def test_uses_fallback_when_local_confidence_low(self):
        decision = select_provider(
            RoutingInput(local_confidence=0.65, local_timed_out=False, grounding_failed=False)
        )
        self.assertEqual(decision.provider, "openai")
        self.assertTrue(decision.fallback_used)
        self.assertEqual(decision.reason, "low_confidence")

    def test_uses_fallback_when_timeout_occurs(self):
        decision = select_provider(
            RoutingInput(local_confidence=0.90, local_timed_out=True, grounding_failed=False)
        )
        self.assertEqual(decision.provider, "openai")
        self.assertEqual(decision.reason, "timeout")

    def test_uses_fallback_when_grounding_fails(self):
        decision = select_provider(
            RoutingInput(local_confidence=0.90, local_timed_out=False, grounding_failed=True)
        )
        self.assertEqual(decision.provider, "openai")
        self.assertEqual(decision.reason, "grounding_failure")

    def test_blocks_fallback_when_cloud_not_allowed(self):
        decision = select_provider(
            RoutingInput(
                local_confidence=0.60,
                local_timed_out=False,
                grounding_failed=False,
                cloud_allowed=False,
            )
        )
        self.assertEqual(decision.provider, "local")
        self.assertFalse(decision.fallback_used)
        self.assertEqual(decision.reason, "cloud_blocked")


if __name__ == "__main__":
    unittest.main()

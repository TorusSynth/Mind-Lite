import unittest

from mind_lite.contracts.sensitivity_gate import SensitivityInput, cloud_eligibility


class SensitivityGatePolicyTests(unittest.TestCase):
    def test_blocks_when_frontmatter_marks_sensitive(self):
        payload = SensitivityInput(
            frontmatter={"sensitive": True},
            tags=[],
            path="Projects/Atlas/note.md",
            content="harmless text",
        )
        result = cloud_eligibility(payload)
        self.assertFalse(result.allowed)
        self.assertIn("frontmatter", result.reasons[0])

    def test_blocks_when_sensitive_tag_present(self):
        payload = SensitivityInput(
            frontmatter={},
            tags=["work", "private"],
            path="Projects/Atlas/note.md",
            content="harmless text",
        )
        result = cloud_eligibility(payload)
        self.assertFalse(result.allowed)
        self.assertIn("tag", result.reasons[0])

    def test_blocks_when_path_matches_protected_prefix(self):
        payload = SensitivityInput(
            frontmatter={},
            tags=[],
            path="Private/Finances/budget.md",
            content="harmless text",
        )
        result = cloud_eligibility(payload)
        self.assertFalse(result.allowed)
        self.assertIn("path", result.reasons[0])

    def test_blocks_when_content_matches_secret_pattern(self):
        payload = SensitivityInput(
            frontmatter={},
            tags=[],
            path="Projects/Atlas/note.md",
            content="OPENAI_API_KEY=sk-test-1234",
        )
        result = cloud_eligibility(payload)
        self.assertFalse(result.allowed)
        self.assertIn("regex", result.reasons[0])

    def test_allows_when_no_rules_trigger(self):
        payload = SensitivityInput(
            frontmatter={"status": "draft"},
            tags=["project"],
            path="Projects/Atlas/plan.md",
            content="This note contains planning text only.",
        )
        result = cloud_eligibility(payload)
        self.assertTrue(result.allowed)
        self.assertEqual(result.reasons, [])


if __name__ == "__main__":
    unittest.main()

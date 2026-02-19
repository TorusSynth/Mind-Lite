import unittest
from unittest.mock import patch

from mind_lite.links.propose_llm import (
    build_link_prompt,
    parse_link_response,
    apply_spam_controls,
    score_links,
)


class TestBuildLinkPrompt(unittest.TestCase):
    def test_includes_source_and_candidates(self):
        source = {"note_id": "s1", "title": "Source Note", "tags": [], "content_preview": "abc"}
        candidates = [
            {"note_id": "c1", "title": "Candidate 1", "tags": [], "content_preview": "def"},
        ]
        prompt = build_link_prompt(source, candidates)
        self.assertIn("Source Note", prompt)
        self.assertIn("Candidate 1", prompt)


class TestParseLinkResponse(unittest.TestCase):
    def test_valid_response(self):
        raw = '{"suggestions": [{"target_note_id": "c1", "confidence": 0.85, "reason": "semantic_similarity"}]}'
        result = parse_link_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target_note_id"], "c1")
        self.assertEqual(result[0]["reason"], "semantic_similarity")

    def test_invalid_reason_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_link_response('{"suggestions": [{"target_note_id": "x", "confidence": 0.5, "reason": "invalid"}]}')
        self.assertIn("shared_project_context, structural_overlap, semantic_similarity", str(ctx.exception))

    def test_missing_suggestions_returns_empty(self):
        result = parse_link_response('{}')
        self.assertEqual(result, [])


class TestApplySpamControls(unittest.TestCase):
    def test_filters_low_confidence(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "b", "confidence": 0.40, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target_note_id"], "a")

    def test_filters_existing_links(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links={"a"}, batch_targets={})
        self.assertEqual(len(result), 0)

    def test_limits_target_saturation(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.80, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.75, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.70, "reason": "semantic_similarity"},
        ]
        batch_targets = {"a": 2}
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets=batch_targets)
        self.assertEqual(len(result), 1)

    def test_limits_max_suggestions(self):
        suggestions = [
            {"target_note_id": str(i), "confidence": 0.80, "reason": "semantic_similarity"}
            for i in range(20)
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        self.assertEqual(len(result), 10)


class TestScoreLinks(unittest.TestCase):
    def test_returns_scored_suggestions(self):
        def mock_llm_call(prompt: str) -> str:
            return '{"suggestions": [{"target_note_id": "c1", "confidence": 0.88, "reason": "shared_project_context"}]}'

        with patch("mind_lite.links.propose_llm._call_llm", side_effect=mock_llm_call):
            source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
            candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
            result = score_links(source, candidates)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["confidence"], 0.88)

    def test_llm_failure_returns_empty(self):
        def mock_llm_fail(prompt):
            return '{"suggestions": []}'

        with patch("mind_lite.links.propose_llm._call_llm", side_effect=mock_llm_fail):
            source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
            candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
            result = score_links(source, candidates)
            self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()

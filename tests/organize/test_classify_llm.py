import unittest
from unittest.mock import patch

from mind_lite.organize.classify_llm import (
    build_classify_prompt,
    parse_classify_response,
    classify_note,
)


class TestBuildClassifyPrompt(unittest.TestCase):
    def test_includes_note_context(self):
        note = {
            "note_id": "abc123",
            "title": "Project Alpha Launch",
            "folder": "Inbox",
            "tags": ["project", "launch"],
            "content_preview": "Planning the Q1 launch...",
        }
        prompt = build_classify_prompt(note)
        self.assertIn("Project Alpha Launch", prompt)
        self.assertIn("project, launch", prompt)
        self.assertIn("Planning the Q1 launch", prompt)


class TestParseClassifyResponse(unittest.TestCase):
    def test_valid_response(self):
        raw = '{"primary": "project", "secondary": ["area"], "confidence": 0.85}'
        result = parse_classify_response(raw)
        self.assertEqual(result, {"primary": "project", "secondary": ["area"], "confidence": 0.85})

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_classify_response("not json")
        self.assertIn("valid JSON", str(ctx.exception))

    def test_missing_primary_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_classify_response('{"secondary": [], "confidence": 0.5}')
        self.assertIn("primary", str(ctx.exception))

    def test_invalid_primary_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_classify_response('{"primary": "invalid", "confidence": 0.5}')
        self.assertIn("archive", str(ctx.exception))

    def test_secondary_excludes_primary(self):
        with self.assertRaises(ValueError) as ctx:
            parse_classify_response('{"primary": "project", "secondary": ["project"], "confidence": 0.8}')
        self.assertIn("cannot repeat primary", str(ctx.exception))

    def test_confidence_out_of_range_clamps(self):
        raw = '{"primary": "resource", "secondary": [], "confidence": 1.5}'
        result = parse_classify_response(raw)
        self.assertEqual(result["confidence"], 1.0)


class TestClassifyNote(unittest.TestCase):
    def test_returns_classified_result(self):
        def mock_llm_call(prompt: str) -> str:
            return '{"primary": "project", "secondary": ["area"], "confidence": 0.82}'

        with patch("mind_lite.organize.classify_llm._call_llm", side_effect=mock_llm_call):
            note = {"note_id": "x", "title": "Test", "folder": "", "tags": [], "content_preview": ""}
            result = classify_note(note)
            self.assertEqual(result["primary"], "project")
            self.assertIn("area", result["secondary"])
            self.assertEqual(result["confidence"], 0.82)

    def test_llm_failure_returns_fallback(self):
        def mock_llm_fail(prompt):
            return '{"primary": "resource", "secondary": [], "confidence": 0.5}'

        with patch("mind_lite.organize.classify_llm._call_llm", side_effect=mock_llm_fail):
            note = {"note_id": "x", "title": "Test", "folder": "", "tags": [], "content_preview": ""}
            result = classify_note(note)
            self.assertEqual(result["primary"], "resource")
            self.assertEqual(result["confidence"], 0.5)


if __name__ == "__main__":
    unittest.main()

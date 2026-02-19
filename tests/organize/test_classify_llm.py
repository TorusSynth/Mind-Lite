import pytest
from mind_lite.organize.classify_llm import (
    build_classify_prompt,
    parse_classify_response,
    classify_note,
)


class TestBuildClassifyPrompt:
    def test_includes_note_context(self):
        note = {
            "note_id": "abc123",
            "title": "Project Alpha Launch",
            "folder": "Inbox",
            "tags": ["project", "launch"],
            "content_preview": "Planning the Q1 launch...",
        }
        prompt = build_classify_prompt(note)
        assert "Project Alpha Launch" in prompt
        assert "project, launch" in prompt
        assert "Planning the Q1 launch" in prompt


class TestParseClassifyResponse:
    def test_valid_response(self):
        raw = '{"primary": "project", "secondary": ["area"], "confidence": 0.85}'
        result = parse_classify_response(raw)
        assert result == {"primary": "project", "secondary": ["area"], "confidence": 0.85}

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="valid JSON"):
            parse_classify_response("not json")

    def test_missing_primary_raises(self):
        with pytest.raises(ValueError, match="primary"):
            parse_classify_response('{"secondary": [], "confidence": 0.5}')

    def test_invalid_primary_raises(self):
        with pytest.raises(ValueError, match="project, area, resource, archive"):
            parse_classify_response('{"primary": "invalid", "confidence": 0.5}')

    def test_secondary_excludes_primary(self):
        with pytest.raises(ValueError, match="cannot repeat primary"):
            parse_classify_response('{"primary": "project", "secondary": ["project"], "confidence": 0.8}')

    def test_confidence_out_of_range_clamps(self):
        raw = '{"primary": "resource", "secondary": [], "confidence": 1.5}'
        result = parse_classify_response(raw)
        assert result["confidence"] == 1.0


class TestClassifyNote:
    def test_returns_classified_result(self, monkeypatch):
        def mock_llm_call(prompt: str) -> str:
            return '{"primary": "project", "secondary": ["area"], "confidence": 0.82}'
        monkeypatch.setattr("mind_lite.organize.classify_llm._call_llm", mock_llm_call)
        
        note = {"note_id": "x", "title": "Test", "folder": "", "tags": [], "content_preview": ""}
        result = classify_note(note)
        assert result["primary"] == "project"
        assert "area" in result["secondary"]
        assert result["confidence"] == 0.82

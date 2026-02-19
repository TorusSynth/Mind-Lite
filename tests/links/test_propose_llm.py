import pytest
from mind_lite.links.propose_llm import (
    build_link_prompt,
    parse_link_response,
    apply_spam_controls,
    score_links,
)


class TestBuildLinkPrompt:
    def test_includes_source_and_candidates(self):
        source = {"note_id": "s1", "title": "Source Note", "tags": [], "content_preview": "abc"}
        candidates = [
            {"note_id": "c1", "title": "Candidate 1", "tags": [], "content_preview": "def"},
        ]
        prompt = build_link_prompt(source, candidates)
        assert "Source Note" in prompt
        assert "Candidate 1" in prompt


class TestParseLinkResponse:
    def test_valid_response(self):
        raw = '{"suggestions": [{"target_note_id": "c1", "confidence": 0.85, "reason": "semantic_similarity"}]}'
        result = parse_link_response(raw)
        assert len(result) == 1
        assert result[0]["target_note_id"] == "c1"
        assert result[0]["reason"] == "semantic_similarity"

    def test_invalid_reason_raises(self):
        with pytest.raises(ValueError, match="shared_project_context, structural_overlap, semantic_similarity"):
            parse_link_response('{"suggestions": [{"target_note_id": "x", "confidence": 0.5, "reason": "invalid"}]}')

    def test_missing_suggestions_returns_empty(self):
        result = parse_link_response('{}')
        assert result == []


class TestApplySpamControls:
    def test_filters_low_confidence(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "b", "confidence": 0.40, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        assert len(result) == 1
        assert result[0]["target_note_id"] == "a"

    def test_filters_existing_links(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
        ]
        result = apply_spam_controls(suggestions, existing_links={"a"}, batch_targets={})
        assert len(result) == 0

    def test_limits_target_saturation(self):
        suggestions = [
            {"target_note_id": "a", "confidence": 0.85, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.80, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.75, "reason": "semantic_similarity"},
            {"target_note_id": "a", "confidence": 0.70, "reason": "semantic_similarity"},
        ]
        batch_targets = {"a": 2}
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets=batch_targets)
        assert len(result) == 1

    def test_limits_max_suggestions(self):
        suggestions = [
            {"target_note_id": str(i), "confidence": 0.80, "reason": "semantic_similarity"}
            for i in range(20)
        ]
        result = apply_spam_controls(suggestions, existing_links=set(), batch_targets={})
        assert len(result) == 10


class TestScoreLinks:
    def test_returns_scored_suggestions(self, monkeypatch):
        def mock_llm_call(prompt: str) -> str:
            return '{"suggestions": [{"target_note_id": "c1", "confidence": 0.88, "reason": "shared_project_context"}]}'
        monkeypatch.setattr("mind_lite.links.propose_llm._call_llm", mock_llm_call)

        source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
        candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
        result = score_links(source, candidates)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.88

    def test_llm_failure_returns_empty(self, monkeypatch):
        def mock_llm_fail(prompt):
            return '{"suggestions": []}'
        monkeypatch.setattr("mind_lite.links.propose_llm._call_llm", mock_llm_fail)

        source = {"note_id": "s1", "title": "Source", "tags": [], "content_preview": ""}
        candidates = [{"note_id": "c1", "title": "C1", "tags": [], "content_preview": ""}]
        result = score_links(source, candidates)
        assert result == []

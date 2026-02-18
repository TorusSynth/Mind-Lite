import unittest

from mind_lite.onboarding.proposal_llm import build_note_prompt, parse_llm_candidates


class ProposalLlmTests(unittest.TestCase):
    def test_parse_llm_candidates_accepts_valid_payload(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "tag_enrichment", '
            '"risk_tier": "medium", "confidence": 0.8, "details": {"tags": ["project"]}}'
            "]}"
        )

        candidates = parse_llm_candidates(raw)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["note_id"], "note-1")
        self.assertEqual(candidates[0]["change_type"], "tag_enrichment")
        self.assertEqual(candidates[0]["risk_tier"], "medium")
        self.assertEqual(candidates[0]["confidence"], 0.8)
        self.assertEqual(candidates[0]["details"], {"tags": ["project"]})

    def test_parse_llm_candidates_rejects_invalid_risk_tier(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "tag_enrichment", '
            '"risk_tier": "critical", "confidence": 0.8, "details": {}}'
            "]}"
        )

        with self.assertRaisesRegex(
            ValueError,
            "proposal\\[0\\].*risk_tier .*critical.*allowed values",
        ):
            parse_llm_candidates(raw)

    def test_parse_llm_candidates_rejects_confidence_out_of_range(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "tag_enrichment", '
            '"risk_tier": "low", "confidence": 1.2, "details": {}}'
            "]}"
        )

        with self.assertRaisesRegex(ValueError, "proposal\\[0\\].*confidence must be in \\[0, 1\\]"):
            parse_llm_candidates(raw)

    def test_parse_llm_candidates_rejects_missing_note_id(self):
        raw = (
            '{"proposals": ['
            '{"change_type": "tag_enrichment", "risk_tier": "low", '
            '"confidence": 0.2, "details": {}}'
            "]}"
        )

        with self.assertRaisesRegex(ValueError, "proposal\\[0\\].*note_id must be a non-empty string"):
            parse_llm_candidates(raw)

    def test_parse_llm_candidates_rejects_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_llm_candidates("{not-json")

    def test_parse_llm_candidates_rejects_non_object_top_level(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            parse_llm_candidates("[]")

    def test_parse_llm_candidates_rejects_proposals_not_list(self):
        with self.assertRaisesRegex(ValueError, '"proposals" as a list'):
            parse_llm_candidates('{"proposals": {}}')

    def test_parse_llm_candidates_rejects_details_not_object(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "tag_enrichment", '
            '"risk_tier": "low", "confidence": 0.5, "details": []}'
            "]}"
        )

        with self.assertRaisesRegex(ValueError, "proposal\\[0\\].*details must be an object"):
            parse_llm_candidates(raw)

    def test_parse_llm_candidates_rejects_bool_confidence(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "tag_enrichment", '
            '"risk_tier": "low", "confidence": true, "details": {}}'
            "]}"
        )

        with self.assertRaisesRegex(ValueError, "proposal\\[0\\].*confidence must be a number"):
            parse_llm_candidates(raw)

    def test_parse_llm_candidates_rejects_invalid_change_type_with_allowed_values(self):
        raw = (
            '{"proposals": ['
            '{"note_id": "note-1", "change_type": "bad_type", '
            '"risk_tier": "low", "confidence": 0.8, "details": {}}'
            "]}"
        )

        with self.assertRaisesRegex(
            ValueError,
            "proposal\\[0\\].*change_type .*bad_type.*allowed values",
        ):
            parse_llm_candidates(raw)

    def test_build_note_prompt_is_deterministic_and_includes_required_fields(self):
        note = {
            "note_id": "alpha-1",
            "title": "Alpha",
            "folder": "projects",
            "tags": ["todo", "urgent"],
            "content_preview": "First line of note",
        }

        prompt = build_note_prompt(note)

        self.assertEqual(
            prompt,
            "note_id: alpha-1\n"
            "title: Alpha\n"
            "folder: projects\n"
            "tags: todo, urgent\n"
            "content_preview: First line of note",
        )

    def test_build_note_prompt_uses_deterministic_fallback_for_unexpected_tags_type(self):
        note = {
            "note_id": "alpha-2",
            "title": "Alpha",
            "folder": "projects",
            "tags": object(),
            "content_preview": "Second line of note",
        }

        prompt = build_note_prompt(note)

        self.assertEqual(
            prompt,
            "note_id: alpha-2\n"
            "title: Alpha\n"
            "folder: projects\n"
            "tags: [invalid tags]\n"
            "content_preview: Second line of note",
        )


if __name__ == "__main__":
    unittest.main()

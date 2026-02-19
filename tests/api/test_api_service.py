import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mind_lite.api.service import ApiService


class ApiServiceTests(unittest.TestCase):
    def test_health_returns_ok(self):
        service = ApiService()
        self.assertEqual(service.health(), {"status": "ok"})

    def test_health_ready_returns_ready(self):
        service = ApiService()
        self.assertEqual(service.health_ready(), {"status": "ready"})

    def test_metrics_exposes_prometheus_text(self):
        service = ApiService()
        metrics = service.metrics()
        self.assertIn("mind_lite_runs_total", metrics)
        self.assertIn("mind_lite_proposals_total", metrics)

    def test_metrics_include_publish_queue_and_published_counts(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_001",
                "title": "Atlas Weekly",
                "prepared_content": "Queued payload",
            }
        )
        service.mark_for_gom(
            {
                "draft_id": "draft_002",
                "title": "Atlas Launch",
                "prepared_content": "Published payload",
            }
        )
        service.confirm_gom(
            {
                "draft_id": "draft_002",
                "published_url": "https://gom.example/posts/atlas-launch",
            }
        )

        metrics = service.metrics()

        self.assertIn("mind_lite_publish_queue_total 1", metrics)
        self.assertIn("mind_lite_publish_published_total 1", metrics)

    def test_analyze_folder_creates_run_record(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") != "a":
                return '{"proposals": []}'
            return (
                '{"proposals":[{"note_id":"a","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            result = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

            self.assertIn("run_id", result)
            self.assertEqual(result["state"], "ready_safe_auto")
            self.assertEqual(result["profile"]["note_count"], 2)

            stored = service.get_run(result["run_id"])
            self.assertEqual(stored["run_id"], result["run_id"])
            self.assertEqual(stored["state"], "ready_safe_auto")

    def test_analyze_folder_sets_ready_safe_auto_when_auto_proposals_exist(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") == "atlas":
                return (
                    '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                    '"risk_tier":"low","confidence":0.91,"details":{"reason":"safe_auto"}}]}'
                )
            return '{"proposals": []}'

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas", encoding="utf-8")
            (root / "other.md").write_text("# Other", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

        self.assertEqual(run["state"], "ready_safe_auto")

    def test_analyze_folder_sets_awaiting_review_when_no_auto_proposals(self):
        service = ApiService()
        transitions: list[tuple[str, str]] = []

        from mind_lite.contracts.run_lifecycle import validate_transition as lifecycle_validate_transition

        def record_validate_transition(current, target):
            transitions.append((current.value, target.value))
            return lifecycle_validate_transition(current, target)

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") == "atlas":
                return (
                    '{"proposals":[{"note_id":"atlas","change_type":"link_add",'
                    '"risk_tier":"medium","confidence":0.75,"details":{"reason":"needs_review"}}]}'
                )
            if note.get("note_id") == "guide":
                return (
                    '{"proposals":[{"note_id":"guide","change_type":"tag_enrichment",'
                    '"risk_tier":"low","confidence":0.79,"details":{"reason":"manual_check"}}]}'
                )
            return '{"proposals": []}'

        service._generate_note_candidate_response = stub_note_llm_response

        with patch("mind_lite.api.service.validate_transition", side_effect=record_validate_transition):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "atlas.md").write_text("# Atlas", encoding="utf-8")
                (root / "guide.md").write_text("# Guide", encoding="utf-8")

                run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

        self.assertEqual(run["state"], "awaiting_review")
        self.assertEqual(
            transitions,
            [
                ("queued", "analyzing"),
                ("analyzing", "awaiting_review"),
            ],
        )

    def test_analyze_folder_default_candidate_generation_returns_usable_proposals(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("# Atlas\nInitial content", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["state"], "ready_safe_auto")
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["note_id"], "a")
        self.assertEqual(proposals[0]["change_type"], "tag_enrichment")
        self.assertEqual(proposals[0]["risk_tier"], "low")

    def test_analyze_folder_empty_directory_returns_no_proposals(self):
        service = ApiService()
        transitions: list[tuple[str, str]] = []

        from mind_lite.contracts.run_lifecycle import validate_transition as lifecycle_validate_transition

        def record_validate_transition(current, target):
            transitions.append((current.value, target.value))
            return lifecycle_validate_transition(current, target)

        with patch("mind_lite.api.service.validate_transition", side_effect=record_validate_transition):
            with tempfile.TemporaryDirectory() as temp_dir:
                run = service.analyze_folder({"folder_path": temp_dir, "mode": "analyze"})
                proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["profile"]["note_count"], 0)
        self.assertEqual(run["state"], "awaiting_review")
        self.assertEqual(len(proposals), 0)
        self.assertEqual(
            transitions,
            [
                ("queued", "analyzing"),
                ("analyzing", "awaiting_review"),
            ],
        )

    def test_get_run_returns_defensive_copy_for_nested_state(self):
        service = ApiService()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            fetched = service.get_run(run["run_id"])
            original_count = fetched["profile"]["note_count"]

            fetched["profile"]["note_count"] = 999
            reread = service.get_run(run["run_id"])

            self.assertEqual(reread["profile"]["note_count"], original_count)

    def test_invalid_folder_raises_value_error(self):
        service = ApiService()
        with self.assertRaises(ValueError):
            service.analyze_folder({"folder_path": "/tmp/does-not-exist-ml", "mode": "analyze"})

    def test_analyze_folders_creates_parent_run_with_batch_entries(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "one"
            folder_two = root / "two"
            folder_one.mkdir()
            folder_two.mkdir()
            service._proposals_by_run["run_1001"] = [{"proposal_id": "run_1001-prop-01"}]
            service._proposals_by_run["run_1002"] = [
                {"proposal_id": "run_1002-prop-01"},
                {"proposal_id": "run_1002-prop-02"},
            ]

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                if folder_path == str(folder_one):
                    return {
                        "run_id": "run_1001",
                        "state": "ready_safe_auto",
                        "profile": {"note_count": 3},
                        "diagnostics": [],
                    }
                if folder_path == str(folder_two):
                    return {
                        "run_id": "run_1002",
                        "state": "awaiting_review",
                        "profile": {"note_count": 1},
                        "diagnostics": [{"note_id": "n2", "error": "parse warning"}],
                    }
                raise AssertionError(f"unexpected folder path: {folder_path}")

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(folder_one), str(folder_two)],
                        "mode": "analyze",
                    }
                )

        self.assertIn("run_id", parent)
        self.assertEqual(parent["batch_total"], 2)
        self.assertEqual(parent["batch_completed"], 2)
        self.assertEqual(len(parent["batches"]), 2)
        self.assertEqual(parent["diagnostics"], [])
        self.assertEqual(parent["state"], "ready_safe_auto")
        stored_parent = service.get_run(parent["run_id"])
        self.assertEqual(stored_parent["run_id"], parent["run_id"])
        self.assertEqual(stored_parent["state"], "ready_safe_auto")

        first = parent["batches"][0]
        second = parent["batches"][1]
        self.assertEqual(
            set(first.keys()),
            {"batch_id", "folder_path", "run_id", "state", "proposal_count", "diagnostics_count", "snapshot_id"},
        )
        self.assertEqual(first["batch_id"], "batch_0001")
        self.assertEqual(first["folder_path"], str(folder_one))
        self.assertEqual(first["run_id"], "run_1001")
        self.assertEqual(first["state"], "ready_safe_auto")
        self.assertEqual(first["proposal_count"], 1)
        self.assertEqual(first["diagnostics_count"], 0)
        self.assertEqual(second["batch_id"], "batch_0002")
        self.assertEqual(second["folder_path"], str(folder_two))
        self.assertEqual(second["run_id"], "run_1002")
        self.assertEqual(second["state"], "awaiting_review")
        self.assertEqual(second["proposal_count"], 2)
        self.assertEqual(second["diagnostics_count"], 1)

    def test_analyze_folders_handles_partial_child_failures(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            healthy = root / "healthy"
            broken = root / "broken"
            healthy.mkdir()
            broken.mkdir()

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                if folder_path == str(healthy):
                    return {
                        "run_id": "run_2001",
                        "state": "ready_safe_auto",
                        "profile": {"note_count": 2},
                        "diagnostics": [],
                    }
                if folder_path == str(broken):
                    raise ValueError("child analysis failed")
                raise AssertionError(f"unexpected folder path: {folder_path}")

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(healthy), str(broken)],
                        "mode": "analyze",
                    }
                )

        self.assertIn("run_id", parent)
        self.assertEqual(parent["batch_total"], 2)
        self.assertEqual(parent["batch_completed"], 2)
        self.assertEqual(len(parent["batches"]), 2)
        self.assertEqual(parent["state"], "ready_safe_auto")

        batches_by_path = {item["folder_path"]: item for item in parent["batches"]}
        self.assertEqual(batches_by_path[str(healthy)]["state"], "ready_safe_auto")
        self.assertEqual(batches_by_path[str(broken)]["state"], "failed_needs_attention")
        self.assertIsNone(batches_by_path[str(broken)]["run_id"])
        self.assertEqual(batches_by_path[str(broken)]["proposal_count"], 0)
        self.assertEqual(batches_by_path[str(broken)]["diagnostics_count"], 1)

        self.assertEqual(len(parent["diagnostics"]), 1)
        self.assertEqual(parent["diagnostics"][0]["batch_id"], "batch_0002")
        self.assertEqual(parent["diagnostics"][0]["folder_path"], str(broken))
        self.assertIn("error", parent["diagnostics"][0])

    def test_analyze_folders_sets_failed_needs_attention_when_all_children_fail(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            broken_one = root / "broken_one"
            broken_two = root / "broken_two"
            broken_one.mkdir()
            broken_two.mkdir()

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                raise ValueError(f"failed child folder: {folder_path}")

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(broken_one), str(broken_two)],
                        "mode": "analyze",
                    }
                )

        self.assertEqual(parent["batch_total"], 2)
        self.assertEqual(parent["batch_completed"], 2)
        self.assertEqual(parent["state"], "failed_needs_attention")
        self.assertEqual(len(parent["diagnostics"]), 2)
        self.assertTrue(all(item["state"] == "failed_needs_attention" for item in parent["batches"]))
        self.assertEqual(parent["batches"][0]["batch_id"], "batch_0001")
        self.assertEqual(parent["batches"][1]["batch_id"], "batch_0002")

    def test_analyze_folders_rejects_invalid_folder_paths_payload(self):
        service = ApiService()

        invalid_payloads = [
            {},
            {"folder_paths": []},
            {"folder_paths": [123]},
            {"folder_paths": ["   "]},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "folder_paths"):
                    service.analyze_folders(payload)

    def test_analyze_folders_raises_unexpected_child_errors(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "folder"
            folder.mkdir()

            with patch.object(service, "_analyze_folder_run", side_effect=RuntimeError("unexpected failure")):
                with self.assertRaisesRegex(RuntimeError, "unexpected failure"):
                    service.analyze_folders({"folder_paths": [str(folder)], "mode": "analyze"})

    def test_analyze_folders_persists_state_once_after_batch_completion(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "one"
            folder_two = root / "two"
            folder_one.mkdir()
            folder_two.mkdir()
            (folder_one / "a.md").write_text("# A\n[[B]]", encoding="utf-8")
            (folder_two / "b.md").write_text("# B", encoding="utf-8")

            with patch.object(service, "_persist_state") as persist_state:
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(folder_one), str(folder_two)],
                        "mode": "analyze",
                    }
                )

        self.assertEqual(parent["batch_completed"], 2)
        self.assertEqual(persist_state.call_count, 1)

    def test_analyze_folders_integration_persists_parent_and_children_deterministically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"
            folder_one = root / "one"
            folder_two = root / "two"
            folder_one.mkdir()
            folder_two.mkdir()
            (folder_one / "a.md").write_text("# A\n[[B]]", encoding="utf-8")
            (folder_two / "b.md").write_text("# B", encoding="utf-8")

            service = ApiService(state_file=str(state_file))
            parent = service.analyze_folders(
                {
                    "folder_paths": [str(folder_one), str(folder_two)],
                    "mode": "analyze",
                }
            )

            self.assertEqual(parent["run_id"], "run_0001")
            self.assertEqual(parent["state"], "ready_safe_auto")
            self.assertEqual(parent["batch_completed"], 2)
            self.assertEqual(
                [item["run_id"] for item in parent["batches"]],
                ["run_0002", "run_0003"],
            )

            payload = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_counter"], 3)
            self.assertEqual(
                sorted(payload["runs"].keys()),
                ["run_0001", "run_0002", "run_0003"],
            )

            reloaded = ApiService(state_file=str(state_file))
            runs = reloaded.list_runs()["runs"]
            self.assertEqual([item["run_id"] for item in runs], ["run_0001", "run_0002", "run_0003"])
            self.assertEqual(reloaded.get_run("run_0001")["batch_completed"], 2)
            self.assertEqual(reloaded.get_run("run_0002")["state"], "ready_safe_auto")
            self.assertEqual(reloaded.get_run("run_0003")["state"], "ready_safe_auto")
            self.assertEqual(len(reloaded.get_run_proposals("run_0002")["proposals"]), 1)
            self.assertEqual(len(reloaded.get_run_proposals("run_0003")["proposals"]), 1)

    def test_proposals_list_and_apply_flow(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") != "a":
                return '{"proposals": []}'
            return (
                '{"proposals":[{"note_id":"a","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            run_id = run["run_id"]

            listed = service.get_run_proposals(run_id)
            self.assertEqual(listed["run_id"], run_id)
            self.assertGreaterEqual(len(listed["proposals"]), 1)

            approve_result = service.approve_run(run_id, {"change_types": ["tag_enrichment"]})
            self.assertEqual(approve_result["run_id"], run_id)
            self.assertEqual(approve_result["state"], "approved")
            self.assertGreaterEqual(approve_result["approved_count"], 1)

            apply_result = service.apply_run(run_id, {"change_types": ["tag_enrichment"]})
            self.assertEqual(apply_result["run_id"], run_id)
            self.assertEqual(apply_result["state"], "applied")
            self.assertIn("snapshot_id", apply_result)
            self.assertGreaterEqual(apply_result["applied_count"], 1)

            rollback_result = service.rollback_run(run_id, {"snapshot_id": apply_result["snapshot_id"]})
            self.assertEqual(rollback_result["run_id"], run_id)
            self.assertEqual(rollback_result["state"], "rolled_back")
            self.assertEqual(rollback_result["rolled_back_snapshot_id"], apply_result["snapshot_id"])

    def test_approve_run_rejects_invalid_run_state(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            return (
                '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"safe_auto"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas", encoding="utf-8")
            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

        service._runs[run["run_id"]]["state"] = "analyzing"
        with self.assertRaisesRegex(ValueError, "run state"):
            service.approve_run(run["run_id"], {"change_types": ["tag_enrichment"]})

    def test_apply_run_rejects_invalid_run_state(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            return (
                '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"safe_auto"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas", encoding="utf-8")
            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

        with self.assertRaisesRegex(ValueError, "run state"):
            service.apply_run(run["run_id"], {"change_types": ["tag_enrichment"]})

    def test_staged_run_progression_analyze_approve_apply(self):
        service = ApiService()
        transitions: list[tuple[str, str]] = []

        from mind_lite.contracts.run_lifecycle import validate_transition as lifecycle_validate_transition

        def record_validate_transition(current, target):
            transitions.append((current.value, target.value))
            return lifecycle_validate_transition(current, target)

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            return (
                '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"safe_auto"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with patch("mind_lite.api.service.validate_transition", side_effect=record_validate_transition):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "atlas.md").write_text("# Atlas", encoding="utf-8")

                run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
                approved = service.approve_run(run["run_id"], {"change_types": ["tag_enrichment"]})
                applied = service.apply_run(run["run_id"], {"change_types": ["tag_enrichment"]})

        self.assertEqual(approved["state"], "approved")
        self.assertEqual(applied["state"], "applied")
        self.assertEqual(
            transitions,
            [
                ("queued", "analyzing"),
                ("analyzing", "ready_safe_auto"),
                ("ready_safe_auto", "awaiting_review"),
                ("awaiting_review", "approved"),
                ("approved", "applied"),
            ],
        )

    def test_get_run_proposals_supports_filters(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") != "a":
                return '{"proposals": []}'
            return (
                '{"proposals":[{"note_id":"a","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            run_id = run["run_id"]

            low_only = service.get_run_proposals(run_id, {"risk_tier": "low"})
            self.assertEqual(len(low_only["proposals"]), 1)
            self.assertEqual(low_only["proposals"][0]["risk_tier"], "low")

            service.approve_run(run_id, {"change_types": ["tag_enrichment"]})
            approved_only = service.get_run_proposals(run_id, {"status": "approved"})
            self.assertEqual(len(approved_only["proposals"]), 1)
            self.assertEqual(approved_only["proposals"][0]["status"], "approved")

    def test_get_run_proposals_returns_defensive_copy_for_nested_state(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            return (
                '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas\nInitial content", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])
            self.assertEqual(len(proposals["proposals"]), 1)

            proposals["proposals"][0]["details"]["reason"] = "mutated"
            reread = service.get_run_proposals(run["run_id"])

            self.assertEqual(reread["proposals"][0]["details"]["reason"], "add_missing_tags")

    def test_analyze_folder_populates_proposals_from_note_candidates(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") != "atlas":
                return "{\"proposals\": []}"
            return (
                '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas\nInitial content", encoding="utf-8")
            (root / "other.md").write_text("# Other\nNo links", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        atlas_proposal = next((item for item in proposals if item.get("note_id") == "atlas"), None)
        self.assertIsNotNone(atlas_proposal)
        self.assertEqual(atlas_proposal["change_type"], "tag_enrichment")
        self.assertEqual(atlas_proposal["details"], {"reason": "add_missing_tags"})

    def test_analyze_folder_handles_partial_note_failures(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") == "atlas":
                return (
                    '{"proposals":[{"note_id":"atlas","change_type":"tag_enrichment",'
                    '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
                )
            return "not-json"

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "atlas.md").write_text("# Atlas\nInitial content", encoding="utf-8")
            (root / "broken.md").write_text("# Broken\nInitial content", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["state"], "ready_safe_auto")
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["note_id"], "atlas")
        self.assertEqual(len(run["diagnostics"]), 1)
        self.assertEqual(run["diagnostics"][0]["note_id"], "broken")
        self.assertIn("error", run["diagnostics"][0])

    def test_analyze_folder_sets_failed_needs_attention_when_all_notes_fail(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") == "broken_one":
                raise RuntimeError("candidate generation timeout")
            return "not-json"

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "broken_one.md").write_text("# Broken one", encoding="utf-8")
            (root / "broken_two.md").write_text("# Broken two", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            stored = service.get_run(run["run_id"])
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["state"], "failed_needs_attention")
        self.assertEqual(stored["state"], "failed_needs_attention")
        self.assertEqual(proposals, [])
        self.assertEqual(len(run["diagnostics"]), 2)

    def test_analyze_folder_sets_failed_needs_attention_for_empty_or_non_string_candidate_output(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str):
            self.assertTrue(prompt)
            if note.get("note_id") == "empty":
                return ""
            if note.get("note_id") == "blank":
                return "   "
            return 123

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "empty.md").write_text("# Empty", encoding="utf-8")
            (root / "blank.md").write_text("# Blank", encoding="utf-8")
            (root / "non_string.md").write_text("# Non String", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["state"], "failed_needs_attention")
        self.assertEqual(proposals, [])
        self.assertEqual(len(run["diagnostics"]), 3)
        diagnostics_by_note_id = {diag["note_id"]: diag for diag in run["diagnostics"]}
        self.assertEqual(
            diagnostics_by_note_id["empty"]["stage"],
            "candidate_generation_empty_output",
        )
        self.assertEqual(
            diagnostics_by_note_id["blank"]["stage"],
            "candidate_generation_empty_output",
        )
        self.assertEqual(
            diagnostics_by_note_id["non_string"]["stage"],
            "candidate_generation_empty_output",
        )

    def test_analyze_folder_treats_empty_candidate_list_as_no_success(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") == "empty_list":
                return '{"proposals": []}'
            return "not-json"

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "empty_list.md").write_text("# Empty list", encoding="utf-8")
            (root / "broken.md").write_text("# Broken", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            proposals = service.get_run_proposals(run["run_id"])["proposals"]

        self.assertEqual(run["state"], "failed_needs_attention")
        self.assertEqual(proposals, [])
        self.assertEqual(len(run["diagnostics"]), 2)
        diagnostics_by_note_id = {diag["note_id"]: diag for diag in run["diagnostics"]}
        self.assertEqual(
            diagnostics_by_note_id["empty_list"]["stage"],
            "candidate_parse_empty_candidates",
        )

    def test_list_runs_returns_created_runs(self):
        service = ApiService()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            first = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            second = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

            listed = service.list_runs()
            listed_ids = [item["run_id"] for item in listed["runs"]]
            self.assertEqual(listed_ids, [first["run_id"], second["run_id"]])

    def test_list_runs_supports_state_filter(self):
        service = ApiService()

        def stub_note_llm_response(note: dict, prompt: str) -> str:
            self.assertTrue(prompt)
            if note.get("note_id") != "a":
                return '{"proposals": []}'
            return (
                '{"proposals":[{"note_id":"a","change_type":"tag_enrichment",'
                '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
            )

        service._generate_note_candidate_response = stub_note_llm_response

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            first = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            second = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            service.approve_run(second["run_id"], {"change_types": ["tag_enrichment"]})
            service.apply_run(second["run_id"], {"change_types": ["tag_enrichment"]})

            filtered = service.list_runs({"state": "applied"})
            self.assertEqual(len(filtered["runs"]), 1)
            self.assertEqual(filtered["runs"][0]["run_id"], second["run_id"])

    def test_list_runs_returns_defensive_copy_for_nested_state(self):
        service = ApiService()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            run = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})
            listed = service.list_runs()
            original_count = listed["runs"][0]["profile"]["note_count"]

            listed["runs"][0]["profile"]["note_count"] = 123
            reread = service.get_run(run["run_id"])

            self.assertEqual(reread["profile"]["note_count"], original_count)

    def test_persists_runs_and_snapshots_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"
            notes_dir = root / "notes"
            notes_dir.mkdir()
            (notes_dir / "a.md").write_text("[[b]]", encoding="utf-8")
            (notes_dir / "b.md").write_text("No links", encoding="utf-8")

            service = ApiService(state_file=str(state_file))

            def stub_note_llm_response(note: dict, prompt: str) -> str:
                self.assertTrue(prompt)
                if note.get("note_id") != "a":
                    return '{"proposals": []}'
                return (
                    '{"proposals":[{"note_id":"a","change_type":"tag_enrichment",'
                    '"risk_tier":"low","confidence":0.91,"details":{"reason":"add_missing_tags"}}]}'
                )

            service._generate_note_candidate_response = stub_note_llm_response

            run = service.analyze_folder({"folder_path": str(notes_dir), "mode": "analyze"})
            service.approve_run(run["run_id"], {"change_types": ["tag_enrichment"]})
            applied = service.apply_run(run["run_id"], {"change_types": ["tag_enrichment"]})

            reloaded = ApiService(state_file=str(state_file))
            reloaded_run = reloaded.get_run(run["run_id"])

            self.assertEqual(reloaded_run["run_id"], run["run_id"])
            self.assertEqual(reloaded_run["state"], "applied")
            self.assertEqual(reloaded_run["snapshot_id"], applied["snapshot_id"])

    def test_persists_publish_queue_and_published_state_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            service.mark_for_gom(
                {
                    "draft_id": "draft_queue",
                    "title": "Queued Draft",
                    "prepared_content": "Queued payload",
                }
            )
            service.mark_for_gom(
                {
                    "draft_id": "draft_published",
                    "title": "Published Draft",
                    "prepared_content": "Published payload",
                }
            )
            service.confirm_gom(
                {
                    "draft_id": "draft_published",
                    "published_url": "https://gom.example/posts/published-draft",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            queue = reloaded.list_gom_queue()
            published = reloaded.list_published()

            self.assertEqual(queue["count"], 1)
            self.assertEqual(queue["items"][0]["draft_id"], "draft_queue")
            self.assertEqual(published["count"], 1)
            self.assertEqual(published["items"][0]["draft_id"], "draft_published")

    def test_persists_ask_idempotency_replay_cache_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            first = service.ask(
                {
                    "query": "What should I work on?",
                    "local_confidence": 0.55,
                    "event_id": "evt_001",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            replayed = reloaded.ask(
                {
                    "query": "Different prompt should be ignored on duplicate",
                    "local_confidence": 0.10,
                    "event_id": "evt_001",
                }
            )

            self.assertTrue(replayed["idempotency"]["duplicate"])
            self.assertEqual(replayed["answer"]["text"], first["answer"]["text"])

    def test_persists_links_apply_idempotency_replay_cache_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            first = service.links_apply(
                {
                    "source_note_id": "n1",
                    "links": [{"target_note_id": "n2", "confidence": 0.9}],
                    "event_id": "evt_links_001",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            replayed = reloaded.links_apply(
                {
                    "source_note_id": "n1",
                    "links": [{"target_note_id": "n3", "confidence": 0.1}],
                    "event_id": "evt_links_001",
                }
            )

            self.assertTrue(replayed["idempotency"]["duplicate"])
            self.assertEqual(replayed["applied_links"], first["applied_links"])

    def test_persists_publish_confirm_idempotency_replay_cache_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            service.mark_for_gom(
                {
                    "draft_id": "draft_030",
                    "title": "Atlas Publish",
                    "prepared_content": "Ready to publish.",
                }
            )
            first = service.confirm_gom(
                {
                    "draft_id": "draft_030",
                    "published_url": "https://gom.example/posts/atlas-publish",
                    "event_id": "evt_confirm_001",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            replayed = reloaded.confirm_gom(
                {
                    "draft_id": "draft_999",
                    "published_url": "https://gom.example/posts/other",
                    "event_id": "evt_confirm_001",
                }
            )

            self.assertTrue(replayed["idempotency"]["duplicate"])
            self.assertEqual(replayed["draft_id"], first["draft_id"])

    def test_persists_publish_mark_idempotency_replay_cache_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            first = service.mark_for_gom(
                {
                    "draft_id": "draft_010",
                    "title": "Project Atlas Weekly",
                    "prepared_content": "Ready for export.",
                    "event_id": "evt_publish_001",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            replayed = reloaded.mark_for_gom(
                {
                    "draft_id": "draft_011",
                    "title": "Different Draft",
                    "prepared_content": "Should be ignored on duplicate event id.",
                    "event_id": "evt_publish_001",
                }
            )

            self.assertTrue(replayed["idempotency"]["duplicate"])
            self.assertEqual(replayed["draft_id"], first["draft_id"])

    def test_sensitivity_check_blocks_payload_with_secret_pattern(self):
        service = ApiService()

        result = service.check_sensitivity(
            {
                "frontmatter": {},
                "tags": ["project"],
                "path": "Projects/Atlas/notes.md",
                "content": "OPENAI_API_KEY=sk-test-1234",
            }
        )

        self.assertFalse(result["allowed"])
        self.assertIn("blocked_by_regex_pattern", result["reasons"])

    def test_sensitivity_policy_summary_exposes_active_rules(self):
        service = ApiService()

        result = service.get_sensitivity_policy()

        self.assertIn("protected_tags", result)
        self.assertIn("protected_path_prefixes", result)
        self.assertIn("secret_pattern_count", result)
        self.assertGreaterEqual(result["secret_pattern_count"], 1)

    def test_routing_policy_summary_exposes_budget_and_thresholds(self):
        service = ApiService()

        result = service.get_routing_policy()

        self.assertIn("routing", result)
        self.assertIn("budget", result)
        self.assertEqual(result["routing"]["local_confidence_threshold"], 0.70)
        self.assertEqual(result["budget"]["status"], "normal")

    def test_ask_uses_openai_fallback_on_low_confidence_when_allowed(self):
        service = ApiService()

        result = service.ask({"query": "What should I work on?", "local_confidence": 0.55})

        self.assertIn("answer", result)
        self.assertIn("provider_trace", result)
        self.assertEqual(result["provider_trace"]["provider"], "openai")
        self.assertTrue(result["provider_trace"]["fallback_used"])
        self.assertEqual(result["provider_trace"]["fallback_reason"], "low_confidence")

    def test_ask_replays_same_response_for_duplicate_event_id(self):
        service = ApiService()

        first = service.ask(
            {
                "query": "What should I work on?",
                "local_confidence": 0.55,
                "event_id": "evt_001",
            }
        )
        second = service.ask(
            {
                "query": "Different prompt should be ignored on duplicate",
                "local_confidence": 0.10,
                "event_id": "evt_001",
            }
        )

        self.assertFalse(first["idempotency"]["duplicate"])
        self.assertTrue(second["idempotency"]["duplicate"])
        self.assertEqual(second["answer"]["text"], first["answer"]["text"])

    def test_ask_blocks_cloud_fallback_when_sensitivity_fails(self):
        service = ApiService()

        result = service.ask(
            {
                "query": "Can I send this?",
                "local_confidence": 0.20,
                "content": "OPENAI_API_KEY=sk-test-1234",
            }
        )

        self.assertEqual(result["provider_trace"]["provider"], "local")
        self.assertFalse(result["provider_trace"]["fallback_used"])
        self.assertEqual(result["provider_trace"]["fallback_reason"], "cloud_blocked")
        self.assertFalse(result["sensitivity"]["allowed"])

    def test_ask_forces_local_when_budget_is_hard_stop(self):
        service = ApiService()
        service._monthly_spend = service._monthly_budget_cap

        result = service.ask({"query": "Need help", "local_timed_out": True})

        self.assertEqual(result["budget"]["status"], "hard_stop")
        self.assertEqual(result["provider_trace"]["provider"], "local")
        self.assertFalse(result["provider_trace"]["fallback_used"])
        self.assertEqual(result["provider_trace"]["fallback_reason"], "cloud_blocked")

    def test_publish_score_returns_gate_pass_for_strong_draft(self):
        service = ApiService()

        result = service.publish_score(
            {
                "draft_id": "draft_001",
                "content": "This is a clear project update with concrete outcomes and next steps." * 4,
            }
        )

        self.assertEqual(result["draft_id"], "draft_001")
        self.assertIn("scores", result)
        self.assertIn("overall", result["scores"])
        self.assertTrue(result["gate_passed"])

    def test_publish_score_blocks_weak_draft(self):
        service = ApiService()

        result = service.publish_score({"draft_id": "draft_002", "content": "TODO"})

        self.assertEqual(result["draft_id"], "draft_002")
        self.assertFalse(result["gate_passed"])
        self.assertLess(result["scores"]["overall"], 0.8)

    def test_publish_prepare_returns_sanitized_draft_payload(self):
        service = ApiService()

        result = service.publish_prepare(
            {
                "draft_id": "draft_003",
                "content": "# Title\n\nThis is a publishable note with links and structure.",
                "target": "gom",
            }
        )

        self.assertEqual(result["draft_id"], "draft_003")
        self.assertEqual(result["target"], "gom")
        self.assertIn("prepared_content", result)
        self.assertTrue(result["sanitized"])

    def test_publish_prepare_requires_draft_id_content_and_target(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.publish_prepare({"draft_id": "draft_004", "content": "text"})

    def test_mark_for_gom_enqueues_publish_candidate(self):
        service = ApiService()

        marked = service.mark_for_gom(
            {
                "draft_id": "draft_010",
                "title": "Project Atlas Weekly",
                "prepared_content": "Ready for export.",
            }
        )
        queue = service.list_gom_queue()

        self.assertEqual(marked["draft_id"], "draft_010")
        self.assertEqual(marked["status"], "queued_for_gom")
        self.assertEqual(queue["count"], 1)
        self.assertEqual(queue["items"][0]["draft_id"], "draft_010")

    def test_mark_for_gom_requires_required_fields(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.mark_for_gom({"draft_id": "draft_011", "title": "Missing content"})

    def test_mark_for_gom_replays_same_response_for_duplicate_event_id(self):
        service = ApiService()

        first = service.mark_for_gom(
            {
                "draft_id": "draft_010",
                "title": "Project Atlas Weekly",
                "prepared_content": "Ready for export.",
                "event_id": "evt_publish_001",
            }
        )
        second = service.mark_for_gom(
            {
                "draft_id": "draft_011",
                "title": "Different Draft",
                "prepared_content": "Should be ignored on duplicate event id.",
                "event_id": "evt_publish_001",
            }
        )

        self.assertFalse(first["idempotency"]["duplicate"])
        self.assertTrue(second["idempotency"]["duplicate"])
        self.assertEqual(second["draft_id"], first["draft_id"])

    def test_export_for_gom_returns_export_payload_for_queued_draft(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_020",
                "title": "Atlas Release",
                "prepared_content": "Ready to publish.",
            }
        )

        exported = service.export_for_gom({"draft_id": "draft_020", "format": "markdown"})

        self.assertEqual(exported["draft_id"], "draft_020")
        self.assertEqual(exported["format"], "markdown")
        self.assertEqual(exported["status"], "export_ready")
        self.assertIn("artifact", exported)

    def test_export_for_gom_replays_same_response_for_duplicate_event_id(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_020",
                "title": "Atlas Release",
                "prepared_content": "Ready to publish.",
            }
        )

        first = service.export_for_gom(
            {
                "draft_id": "draft_020",
                "format": "markdown",
                "event_id": "evt_export_001",
            }
        )
        second = service.export_for_gom(
            {
                "draft_id": "missing",
                "format": "html",
                "event_id": "evt_export_001",
            }
        )

        self.assertFalse(first["idempotency"]["duplicate"])
        self.assertTrue(second["idempotency"]["duplicate"])
        self.assertEqual(second["draft_id"], first["draft_id"])
        self.assertEqual(second["format"], first["format"])
        self.assertEqual(second["artifact"], first["artifact"])

    def test_export_for_gom_rejects_unknown_draft(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.export_for_gom({"draft_id": "missing", "format": "markdown"})

    def test_export_for_gom_rejects_blank_event_id(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_020",
                "title": "Atlas Release",
                "prepared_content": "Ready to publish.",
            }
        )

        with self.assertRaisesRegex(ValueError, "event_id"):
            service.export_for_gom(
                {
                    "draft_id": "draft_020",
                    "format": "markdown",
                    "event_id": "   ",
                }
            )

    def test_confirm_gom_marks_queue_item_as_published(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_030",
                "title": "Atlas Publish",
                "prepared_content": "Ready to publish.",
            }
        )

        result = service.confirm_gom(
            {
                "draft_id": "draft_030",
                "published_url": "https://gom.example/posts/atlas-publish",
            }
        )
        queue = service.list_gom_queue()

        self.assertEqual(result["draft_id"], "draft_030")
        self.assertEqual(result["status"], "published")
        self.assertEqual(result["published_url"], "https://gom.example/posts/atlas-publish")
        self.assertEqual(queue["count"], 0)

    def test_confirm_gom_rejects_unknown_draft(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.confirm_gom(
                {
                    "draft_id": "missing",
                    "published_url": "https://gom.example/posts/missing",
                }
            )

    def test_confirm_gom_replays_same_response_for_duplicate_event_id(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_030",
                "title": "Atlas Publish",
                "prepared_content": "Ready to publish.",
            }
        )

        first = service.confirm_gom(
            {
                "draft_id": "draft_030",
                "published_url": "https://gom.example/posts/atlas-publish",
                "event_id": "evt_confirm_001",
            }
        )
        second = service.confirm_gom(
            {
                "draft_id": "draft_999",
                "published_url": "https://gom.example/posts/other",
                "event_id": "evt_confirm_001",
            }
        )

        self.assertFalse(first["idempotency"]["duplicate"])
        self.assertTrue(second["idempotency"]["duplicate"])
        self.assertEqual(second["draft_id"], first["draft_id"])

    def test_list_published_returns_confirmed_items(self):
        service = ApiService()
        service.mark_for_gom(
            {
                "draft_id": "draft_040",
                "title": "Atlas Journal",
                "prepared_content": "Ready.",
            }
        )
        service.confirm_gom(
            {
                "draft_id": "draft_040",
                "published_url": "https://gom.example/posts/atlas-journal",
            }
        )

        result = service.list_published()

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["draft_id"], "draft_040")
        self.assertEqual(result["items"][0]["status"], "published")

    def test_organize_classify_returns_para_labels(self):
        service = ApiService()

        def mock_classify(note):
            if note.get("note_id") == "n1":
                return {"primary": "project", "secondary": [], "confidence": 0.86}
            return {"primary": "resource", "secondary": [], "confidence": 0.79}

        with patch("mind_lite.organize.classify_llm.classify_note", side_effect=mock_classify):
            result = service.organize_classify(
                {
                    "notes": [
                        {"note_id": "n1", "title": "Project Atlas Weekly Plan"},
                        {"note_id": "n2", "title": "Reference Notes: Zettelkasten"},
                    ]
                }
            )

        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["results"][0]["note_id"], "n1")
        self.assertEqual(result["results"][0]["primary_para"], "project")
        self.assertEqual(result["results"][1]["note_id"], "n2")
        self.assertEqual(result["results"][1]["primary_para"], "resource")

    def test_organize_classify_requires_note_id(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.organize_classify({"notes": [{}]})

    def test_links_propose_returns_scored_suggestions(self):
        service = ApiService()

        result = service.links_propose(
            {
                "source_note_id": "n1",
                "candidate_notes": [
                    {"note_id": "n2", "title": "Atlas Architecture"},
                    {"note_id": "n3", "title": "Random Grocery List"},
                ],
            }
        )

        self.assertEqual(result["source_note_id"], "n1")
        self.assertEqual(len(result["suggestions"]), 2)
        self.assertEqual(result["suggestions"][0]["target_note_id"], "n2")
        self.assertGreater(result["suggestions"][0]["confidence"], result["suggestions"][1]["confidence"])

    def test_links_propose_requires_source_and_candidates(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.links_propose({"source_note_id": "n1", "candidate_notes": []})

    def test_links_apply_marks_selected_links_as_applied(self):
        service = ApiService()

        result = service.links_apply(
            {
                "source_note_id": "n1",
                "links": [
                    {"target_note_id": "n2", "confidence": 0.88},
                    {"target_note_id": "n3", "confidence": 0.79},
                ],
                "min_confidence": 0.8,
            }
        )

        self.assertEqual(result["source_note_id"], "n1")
        self.assertEqual(result["applied_count"], 1)
        self.assertEqual(result["applied_links"][0]["target_note_id"], "n2")

    def test_links_apply_requires_non_empty_links(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.links_apply({"source_note_id": "n1", "links": []})

    def test_links_apply_replays_same_response_for_duplicate_event_id(self):
        service = ApiService()

        first = service.links_apply(
            {
                "source_note_id": "n1",
                "links": [{"target_note_id": "n2", "confidence": 0.9}],
                "event_id": "evt_links_001",
            }
        )
        second = service.links_apply(
            {
                "source_note_id": "n1",
                "links": [{"target_note_id": "n3", "confidence": 0.1}],
                "event_id": "evt_links_001",
            }
        )

        self.assertFalse(first["idempotency"]["duplicate"])
        self.assertTrue(second["idempotency"]["duplicate"])
        self.assertEqual(second["applied_links"], first["applied_links"])

    def test_organize_propose_structure_returns_manual_suggestions(self):
        service = ApiService()

        result = service.organize_propose_structure(
            {
                "notes": [
                    {"note_id": "n1", "title": "Atlas Scratchpad", "folder": "Inbox"},
                    {"note_id": "n2", "title": "Atlas Architecture", "folder": "Projects/Atlas"},
                ]
            }
        )

        self.assertEqual(len(result["proposals"]), 2)
        self.assertEqual(result["proposals"][0]["note_id"], "n1")
        self.assertEqual(result["proposals"][0]["action_mode"], "manual")
        self.assertIn("proposed_folder", result["proposals"][0])

    def test_organize_propose_structure_requires_notes(self):
        service = ApiService()

        with self.assertRaises(ValueError):
            service.organize_propose_structure({"notes": []})

    def test_batch_entry_has_snapshot_id_field_initially_null(self):
        service = ApiService()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "one"
            folder_two = root / "two"
            folder_one.mkdir()
            folder_two.mkdir()

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                if folder_path == str(folder_one):
                    return {
                        "run_id": "run_3001",
                        "state": "ready_safe_auto",
                        "profile": {"note_count": 1},
                        "diagnostics": [],
                    }
                if folder_path == str(folder_two):
                    return {
                        "run_id": "run_3002",
                        "state": "awaiting_review",
                        "profile": {"note_count": 2},
                        "diagnostics": [],
                    }
                raise AssertionError(f"unexpected folder path: {folder_path}")

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(folder_one), str(folder_two)],
                        "mode": "analyze",
                    }
                )

        self.assertEqual(len(parent["batches"]), 2)
        for batch in parent["batches"]:
            self.assertIn("snapshot_id", batch)
            self.assertIsNone(batch["snapshot_id"])

    def test_batch_checkpoint_updated_after_child_apply(self):
        service = ApiService()
        service._proposals_by_run["run_4001"] = [
            {"proposal_id": "run_4001-prop-01", "status": "approved", "change_type": "tag_enrichment"}
        ]
        service._runs["run_4001"] = {
            "run_id": "run_4001",
            "state": "ready_safe_auto",
            "profile": {"note_count": 1},
            "diagnostics": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "one"
            folder_one.mkdir()

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                return {
                    "run_id": "run_4001",
                    "state": "ready_safe_auto",
                    "profile": {"note_count": 1},
                    "diagnostics": [],
                }

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(folder_one)],
                        "mode": "analyze",
                    }
                )

            service.approve_run("run_4001", {"change_types": ["tag_enrichment"]})
            apply_result = service.apply_run("run_4001", {"change_types": ["tag_enrichment"]})

        self.assertIn("snapshot_id", apply_result)
        self.assertIsNotNone(apply_result["snapshot_id"])

        updated_parent = service.get_run(parent["run_id"])
        first_batch = updated_parent["batches"][0]
        self.assertIn("snapshot_id", first_batch)
        self.assertEqual(first_batch["snapshot_id"], apply_result["snapshot_id"])

    def test_multiple_batch_checkpoints_tracked_correctly(self):
        service = ApiService()
        service._proposals_by_run["run_5001"] = [
            {"proposal_id": "run_5001-prop-01", "status": "approved", "change_type": "tag_enrichment"}
        ]
        service._proposals_by_run["run_5002"] = [
            {"proposal_id": "run_5002-prop-01", "status": "approved", "change_type": "tag_enrichment"}
        ]
        service._runs["run_5001"] = {
            "run_id": "run_5001",
            "state": "ready_safe_auto",
            "profile": {"note_count": 1},
            "diagnostics": [],
        }
        service._runs["run_5002"] = {
            "run_id": "run_5002",
            "state": "ready_safe_auto",
            "profile": {"note_count": 2},
            "diagnostics": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "one"
            folder_two = root / "two"
            folder_one.mkdir()
            folder_two.mkdir()

            def stub_analyze_folder_run(folder_path: object, *, mode: str, persist: bool) -> dict:
                self.assertEqual(mode, "analyze")
                self.assertFalse(persist)
                if folder_path == str(folder_one):
                    return {
                        "run_id": "run_5001",
                        "state": "ready_safe_auto",
                        "profile": {"note_count": 1},
                        "diagnostics": [],
                    }
                if folder_path == str(folder_two):
                    return {
                        "run_id": "run_5002",
                        "state": "ready_safe_auto",
                        "profile": {"note_count": 2},
                        "diagnostics": [],
                    }
                raise AssertionError(f"unexpected folder path: {folder_path}")

            with patch.object(service, "_analyze_folder_run", side_effect=stub_analyze_folder_run):
                parent = service.analyze_folders(
                    {
                        "folder_paths": [str(folder_one), str(folder_two)],
                        "mode": "analyze",
                    }
                )

            service.approve_run("run_5001", {"change_types": ["tag_enrichment"]})
            apply_one = service.apply_run("run_5001", {"change_types": ["tag_enrichment"]})

            service.approve_run("run_5002", {"change_types": ["tag_enrichment"]})
            apply_two = service.apply_run("run_5002", {"change_types": ["tag_enrichment"]})

        updated_parent = service.get_run(parent["run_id"])

        self.assertIn("applied_batch_ids", updated_parent)
        self.assertEqual(set(updated_parent["applied_batch_ids"]), {"run_5001", "run_5002"})

        batches_by_run = {b["run_id"]: b for b in updated_parent["batches"]}
        self.assertEqual(batches_by_run["run_5001"]["snapshot_id"], apply_one["snapshot_id"])
        self.assertEqual(batches_by_run["run_5002"]["snapshot_id"], apply_two["snapshot_id"])

    def test_full_batch_checkpoint_flow_from_analyze_to_apply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder_one = root / "notes_alpha"
            folder_two = root / "notes_beta"
            folder_one.mkdir()
            folder_two.mkdir()
            (folder_one / "first.md").write_text("# First Note\nContent for first", encoding="utf-8")
            (folder_two / "second.md").write_text("# Second Note\nContent for second", encoding="utf-8")

            service = ApiService()
            parent = service.analyze_folders(
                {
                    "folder_paths": [str(folder_one), str(folder_two)],
                    "mode": "analyze",
                }
            )

            self.assertEqual(parent["batch_total"], 2)
            self.assertEqual(parent["batch_completed"], 2)
            self.assertEqual(len(parent["batches"]), 2)
            self.assertEqual(parent["state"], "ready_safe_auto")
            for batch in parent["batches"]:
                self.assertIn("snapshot_id", batch)
                self.assertIsNone(batch["snapshot_id"])

            child_run_ids = [batch["run_id"] for batch in parent["batches"]]
            self.assertEqual(len(child_run_ids), 2)
            self.assertTrue(all(rid is not None for rid in child_run_ids))

            apply_results = []
            for child_run_id in child_run_ids:
                service.approve_run(child_run_id, {"change_types": ["tag_enrichment"]})
                apply_result = service.apply_run(child_run_id, {"change_types": ["tag_enrichment"]})
                self.assertEqual(apply_result["state"], "applied")
                self.assertIn("snapshot_id", apply_result)
                self.assertIsNotNone(apply_result["snapshot_id"])
                apply_results.append(apply_result)

            updated_parent = service.get_run(parent["run_id"])
            self.assertIn("applied_batch_ids", updated_parent)
            self.assertEqual(set(updated_parent["applied_batch_ids"]), set(child_run_ids))

            batches_by_run = {b["run_id"]: b for b in updated_parent["batches"]}
            for child_run_id, apply_result in zip(child_run_ids, apply_results):
                batch = batches_by_run[child_run_id]
                self.assertEqual(batch["snapshot_id"], apply_result["snapshot_id"])

            first_child_id = child_run_ids[0]
            first_snapshot = apply_results[0]["snapshot_id"]
            rollback_result = service.rollback_run(first_child_id, {"snapshot_id": first_snapshot})
            self.assertEqual(rollback_result["run_id"], first_child_id)
            self.assertEqual(rollback_result["state"], "rolled_back")
            self.assertEqual(rollback_result["rolled_back_snapshot_id"], first_snapshot)


class ApiServiceStatePersistenceTests(unittest.TestCase):
    def test_persists_publish_export_idempotency_replay_cache_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"

            service = ApiService(state_file=str(state_file))
            service.mark_for_gom(
                {
                    "draft_id": "draft_020",
                    "title": "Atlas Release",
                    "prepared_content": "Ready to publish.",
                }
            )
            first = service.export_for_gom(
                {
                    "draft_id": "draft_020",
                    "format": "markdown",
                    "event_id": "evt_export_001",
                }
            )

            reloaded = ApiService(state_file=str(state_file))
            replayed = reloaded.export_for_gom(
                {
                    "draft_id": "draft_999",
                    "format": "html",
                    "event_id": "evt_export_001",
                }
            )

            self.assertTrue(replayed["idempotency"]["duplicate"])
            self.assertEqual(replayed["draft_id"], first["draft_id"])
            self.assertEqual(replayed["format"], first["format"])
            self.assertEqual(replayed["artifact"], first["artifact"])


class TestOrganizeClassifyLLM:
    def test_uses_llm_classification(self, monkeypatch):
        from mind_lite.api.service import ApiService

        def mock_classify(note):
            return {
                "note_id": note["note_id"],
                "primary": "project",
                "secondary": ["area"],
                "confidence": 0.88,
            }
        monkeypatch.setattr("mind_lite.organize.classify_llm.classify_note", mock_classify)

        service = ApiService()
        result = service.organize_classify({
            "notes": [{"note_id": "x", "title": "Test Note", "folder": "", "tags": [], "content_preview": ""}]
        })
        assert result["results"][0]["primary_para"] == "project"
        assert result["results"][0]["secondary_para"] == ["area"]
        assert result["results"][0]["confidence"] == 0.88
        assert result["results"][0]["action_mode"] == "auto"


if __name__ == "__main__":
    unittest.main()

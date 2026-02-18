import tempfile
import unittest
from pathlib import Path

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

    def test_analyze_folder_creates_run_record(self):
        service = ApiService()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            result = service.analyze_folder({"folder_path": str(root), "mode": "analyze"})

            self.assertIn("run_id", result)
            self.assertEqual(result["state"], "analyzing")
            self.assertEqual(result["profile"]["note_count"], 2)

            stored = service.get_run(result["run_id"])
            self.assertEqual(stored["run_id"], result["run_id"])
            self.assertEqual(stored["state"], "analyzing")

    def test_invalid_folder_raises_value_error(self):
        service = ApiService()
        with self.assertRaises(ValueError):
            service.analyze_folder({"folder_path": "/tmp/does-not-exist-ml", "mode": "analyze"})

    def test_proposals_list_and_apply_flow(self):
        service = ApiService()
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

    def test_persists_runs_and_snapshots_to_state_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state.json"
            notes_dir = root / "notes"
            notes_dir.mkdir()
            (notes_dir / "a.md").write_text("[[b]]", encoding="utf-8")
            (notes_dir / "b.md").write_text("No links", encoding="utf-8")

            service = ApiService(state_file=str(state_file))
            run = service.analyze_folder({"folder_path": str(notes_dir), "mode": "analyze"})
            applied = service.apply_run(run["run_id"], {"change_types": ["tag_enrichment"]})

            reloaded = ApiService(state_file=str(state_file))
            reloaded_run = reloaded.get_run(run["run_id"])

            self.assertEqual(reloaded_run["run_id"], run["run_id"])
            self.assertEqual(reloaded_run["state"], "applied")
            self.assertEqual(reloaded_run["snapshot_id"], applied["snapshot_id"])

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


if __name__ == "__main__":
    unittest.main()

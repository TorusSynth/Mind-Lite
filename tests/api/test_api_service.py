import tempfile
import unittest
from pathlib import Path

from mind_lite.api.service import ApiService


class ApiServiceTests(unittest.TestCase):
    def test_health_returns_ok(self):
        service = ApiService()
        self.assertEqual(service.health(), {"status": "ok"})

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

            apply_result = service.apply_run(run_id, {"change_types": ["tag_enrichment"]})
            self.assertEqual(apply_result["run_id"], run_id)
            self.assertEqual(apply_result["state"], "applied")
            self.assertIn("snapshot_id", apply_result)
            self.assertGreaterEqual(apply_result["applied_count"], 1)


if __name__ == "__main__":
    unittest.main()

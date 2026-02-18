import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

from mind_lite.api.http_server import create_server


class HttpServerTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.01)
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def test_health_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_runs_history_endpoint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            conn = HTTPConnection(self.host, self.port, timeout=2)
            payload = {"folder_path": str(root), "mode": "analyze"}
            conn.request(
                "POST",
                "/onboarding/analyze-folder",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            analyze_resp = conn.getresponse()
            self.assertEqual(analyze_resp.status, 200)
            analyze_resp.read()

            conn.request("GET", "/runs")
            runs_resp = conn.getresponse()
            runs_body = json.loads(runs_resp.read().decode("utf-8"))
            conn.close()

            self.assertEqual(runs_resp.status, 200)
            self.assertEqual(len(runs_body["runs"]), 1)

    def test_analyze_and_get_run_endpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            conn = HTTPConnection(self.host, self.port, timeout=2)
            payload = {"folder_path": str(root), "mode": "analyze"}
            conn.request(
                "POST",
                "/onboarding/analyze-folder",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            analyzed = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(resp.status, 200)

            run_id = analyzed["run_id"]
            conn.request("GET", f"/runs/{run_id}")
            run_resp = conn.getresponse()
            run_body = json.loads(run_resp.read().decode("utf-8"))
            conn.close()

            self.assertEqual(run_resp.status, 200)
            self.assertEqual(run_body["run_id"], run_id)
            self.assertEqual(run_body["profile"]["note_count"], 2)

    def test_proposals_and_apply_endpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.md").write_text("[[b]]", encoding="utf-8")
            (root / "b.md").write_text("No links", encoding="utf-8")

            conn = HTTPConnection(self.host, self.port, timeout=2)
            payload = {"folder_path": str(root), "mode": "analyze"}
            conn.request(
                "POST",
                "/onboarding/analyze-folder",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            analyzed_resp = conn.getresponse()
            analyzed = json.loads(analyzed_resp.read().decode("utf-8"))
            self.assertEqual(analyzed_resp.status, 200)
            run_id = analyzed["run_id"]

            conn.request("GET", f"/runs/{run_id}/proposals")
            list_resp = conn.getresponse()
            listed = json.loads(list_resp.read().decode("utf-8"))
            self.assertEqual(list_resp.status, 200)
            self.assertEqual(listed["run_id"], run_id)

            apply_payload = {"change_types": ["tag_enrichment"]}
            conn.request(
                "POST",
                f"/runs/{run_id}/apply",
                body=json.dumps(apply_payload),
                headers={"Content-Type": "application/json"},
            )
            apply_resp = conn.getresponse()
            applied = json.loads(apply_resp.read().decode("utf-8"))
            conn.close()

            self.assertEqual(apply_resp.status, 200)
            self.assertEqual(applied["run_id"], run_id)
            self.assertEqual(applied["state"], "applied")
            self.assertIn("snapshot_id", applied)

            rollback_payload = {"snapshot_id": applied["snapshot_id"]}
            conn = HTTPConnection(self.host, self.port, timeout=2)
            conn.request(
                "POST",
                f"/runs/{run_id}/rollback",
                body=json.dumps(rollback_payload),
                headers={"Content-Type": "application/json"},
            )
            rollback_resp = conn.getresponse()
            rollback_body = json.loads(rollback_resp.read().decode("utf-8"))
            conn.close()

            self.assertEqual(rollback_resp.status, 200)
            self.assertEqual(rollback_body["run_id"], run_id)
            self.assertEqual(rollback_body["state"], "rolled_back")

    def test_persists_runs_across_server_restarts_when_state_file_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "server-state.json"
            notes_dir = root / "notes"
            notes_dir.mkdir()
            (notes_dir / "a.md").write_text("[[b]]", encoding="utf-8")
            (notes_dir / "b.md").write_text("No links", encoding="utf-8")

            first_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
            first_thread.start()
            time.sleep(0.01)
            first_host, first_port = first_server.server_address

            conn = HTTPConnection(first_host, first_port, timeout=2)
            payload = {"folder_path": str(notes_dir), "mode": "analyze"}
            conn.request(
                "POST",
                "/onboarding/analyze-folder",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            analyze_resp = conn.getresponse()
            self.assertEqual(analyze_resp.status, 200)
            analyze_resp.read()
            conn.close()

            first_server.shutdown()
            first_server.server_close()
            first_thread.join(timeout=1)

            second_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            second_thread = threading.Thread(target=second_server.serve_forever, daemon=True)
            second_thread.start()
            time.sleep(0.01)
            second_host, second_port = second_server.server_address

            conn = HTTPConnection(second_host, second_port, timeout=2)
            conn.request("GET", "/runs")
            runs_resp = conn.getresponse()
            runs_body = json.loads(runs_resp.read().decode("utf-8"))
            conn.close()

            second_server.shutdown()
            second_server.server_close()
            second_thread.join(timeout=1)

            self.assertEqual(runs_resp.status, 200)
            self.assertEqual(len(runs_body["runs"]), 1)


if __name__ == "__main__":
    unittest.main()

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

    def test_health_ready_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request("GET", "/health/ready")
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {"status": "ready"})

    def test_metrics_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request("GET", "/metrics")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertIn("mind_lite_runs_total", body)
        self.assertIn("mind_lite_proposals_total", body)

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

            approve_payload = {"change_types": ["tag_enrichment"]}
            conn.request(
                "POST",
                f"/runs/{run_id}/approve",
                body=json.dumps(approve_payload),
                headers={"Content-Type": "application/json"},
            )
            approve_resp = conn.getresponse()
            approved = json.loads(approve_resp.read().decode("utf-8"))
            self.assertEqual(approve_resp.status, 200)
            self.assertEqual(approved["run_id"], run_id)
            self.assertEqual(approved["state"], "approved")

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

    def test_sensitivity_check_endpoint(self):
        payload = {
            "frontmatter": {},
            "tags": ["project"],
            "path": "Projects/Atlas/notes.md",
            "content": "OPENAI_API_KEY=sk-test-1234",
        }

        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/policy/sensitivity/check",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertFalse(body["allowed"])
        self.assertIn("blocked_by_regex_pattern", body["reasons"])

    def test_sensitivity_policy_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request("GET", "/policy/sensitivity")
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertIn("protected_tags", body)
        self.assertIn("protected_path_prefixes", body)
        self.assertIn("secret_pattern_count", body)

    def test_routing_policy_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request("GET", "/policy/routing")
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertIn("routing", body)
        self.assertIn("budget", body)
        self.assertEqual(body["budget"]["status"], "normal")

    def test_ask_endpoint(self):
        payload = {"query": "What should I work on?", "local_confidence": 0.55}
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/ask",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertIn("answer", body)
        self.assertIn("provider_trace", body)
        self.assertEqual(body["provider_trace"]["provider"], "openai")
        self.assertTrue(body["provider_trace"]["fallback_used"])

    def test_ask_endpoint_requires_query(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/ask",
            body=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_publish_score_endpoint(self):
        payload = {
            "draft_id": "draft_001",
            "content": "This is a clear project update with concrete outcomes and next steps." * 4,
        }
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/score",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body["draft_id"], "draft_001")
        self.assertIn("scores", body)
        self.assertTrue(body["gate_passed"])

    def test_publish_score_endpoint_requires_draft_id_and_content(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/score",
            body=json.dumps({"draft_id": "draft_001"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_publish_prepare_endpoint(self):
        payload = {
            "draft_id": "draft_003",
            "content": "# Title\n\nThis is a publishable note with links and structure.",
            "target": "gom",
        }
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/prepare",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body["draft_id"], "draft_003")
        self.assertEqual(body["target"], "gom")
        self.assertTrue(body["sanitized"])

    def test_publish_prepare_endpoint_requires_target(self):
        payload = {
            "draft_id": "draft_003",
            "content": "# Title\n\nThis is a publishable note with links and structure.",
        }
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/prepare",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_mark_for_gom_and_queue_endpoints(self):
        payload = {
            "draft_id": "draft_010",
            "title": "Project Atlas Weekly",
            "prepared_content": "Ready for export.",
        }

        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        mark_resp = conn.getresponse()
        mark_body = json.loads(mark_resp.read().decode("utf-8"))
        self.assertEqual(mark_resp.status, 200)
        self.assertEqual(mark_body["status"], "queued_for_gom")

        conn.request("GET", "/publish/gom-queue")
        queue_resp = conn.getresponse()
        queue_body = json.loads(queue_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(queue_resp.status, 200)
        self.assertEqual(queue_body["count"], 1)
        self.assertEqual(queue_body["items"][0]["draft_id"], "draft_010")

    def test_mark_for_gom_requires_prepared_content(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps({"draft_id": "draft_010", "title": "No content"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_export_for_gom_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        mark_payload = {
            "draft_id": "draft_020",
            "title": "Atlas Release",
            "prepared_content": "Ready to publish.",
        }
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(mark_payload),
            headers={"Content-Type": "application/json"},
        )
        mark_resp = conn.getresponse()
        self.assertEqual(mark_resp.status, 200)
        mark_resp.read()

        export_payload = {"draft_id": "draft_020", "format": "markdown"}
        conn.request(
            "POST",
            "/publish/export-for-gom",
            body=json.dumps(export_payload),
            headers={"Content-Type": "application/json"},
        )
        export_resp = conn.getresponse()
        export_body = json.loads(export_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(export_resp.status, 200)
        self.assertEqual(export_body["draft_id"], "draft_020")
        self.assertEqual(export_body["status"], "export_ready")

    def test_export_for_gom_endpoint_rejects_unknown_draft(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/export-for-gom",
            body=json.dumps({"draft_id": "missing", "format": "markdown"}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_confirm_gom_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        mark_payload = {
            "draft_id": "draft_030",
            "title": "Atlas Publish",
            "prepared_content": "Ready to publish.",
        }
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(mark_payload),
            headers={"Content-Type": "application/json"},
        )
        mark_resp = conn.getresponse()
        self.assertEqual(mark_resp.status, 200)
        mark_resp.read()

        confirm_payload = {
            "draft_id": "draft_030",
            "published_url": "https://gom.example/posts/atlas-publish",
        }
        conn.request(
            "POST",
            "/publish/confirm-gom",
            body=json.dumps(confirm_payload),
            headers={"Content-Type": "application/json"},
        )
        confirm_resp = conn.getresponse()
        confirm_body = json.loads(confirm_resp.read().decode("utf-8"))
        self.assertEqual(confirm_resp.status, 200)
        self.assertEqual(confirm_body["status"], "published")

        conn.request("GET", "/publish/gom-queue")
        queue_resp = conn.getresponse()
        queue_body = json.loads(queue_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(queue_resp.status, 200)
        self.assertEqual(queue_body["count"], 0)

    def test_confirm_gom_endpoint_requires_known_draft(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/confirm-gom",
            body=json.dumps(
                {
                    "draft_id": "missing",
                    "published_url": "https://gom.example/posts/missing",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()

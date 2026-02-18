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

    def test_metrics_endpoint_includes_publish_counts(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(
                {
                    "draft_id": "draft_001",
                    "title": "Atlas Weekly",
                    "prepared_content": "Queued payload",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        mark_resp_1 = conn.getresponse()
        self.assertEqual(mark_resp_1.status, 200)
        mark_resp_1.read()

        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(
                {
                    "draft_id": "draft_002",
                    "title": "Atlas Launch",
                    "prepared_content": "Published payload",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        mark_resp_2 = conn.getresponse()
        self.assertEqual(mark_resp_2.status, 200)
        mark_resp_2.read()

        conn.request(
            "POST",
            "/publish/confirm-gom",
            body=json.dumps(
                {
                    "draft_id": "draft_002",
                    "published_url": "https://gom.example/posts/atlas-launch",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        confirm_resp = conn.getresponse()
        self.assertEqual(confirm_resp.status, 200)
        confirm_resp.read()

        conn.request("GET", "/metrics")
        metrics_resp = conn.getresponse()
        metrics_body = metrics_resp.read().decode("utf-8")
        conn.close()

        self.assertEqual(metrics_resp.status, 200)
        self.assertIn("mind_lite_publish_queue_total 1", metrics_body)
        self.assertIn("mind_lite_publish_published_total 1", metrics_body)

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

            conn.request("GET", f"/runs/{run_id}/proposals?risk_tier=low")
            filtered_resp = conn.getresponse()
            filtered = json.loads(filtered_resp.read().decode("utf-8"))
            self.assertEqual(filtered_resp.status, 200)
            self.assertEqual(len(filtered["proposals"]), 1)
            self.assertEqual(filtered["proposals"][0]["risk_tier"], "low")

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

    def test_persists_publish_queue_and_published_across_server_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "server-state.json"

            first_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
            first_thread.start()
            time.sleep(0.01)
            first_host, first_port = first_server.server_address

            conn = HTTPConnection(first_host, first_port, timeout=2)
            conn.request(
                "POST",
                "/publish/mark-for-gom",
                body=json.dumps(
                    {
                        "draft_id": "draft_queue",
                        "title": "Queued Draft",
                        "prepared_content": "Queued payload",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            mark_resp_1 = conn.getresponse()
            self.assertEqual(mark_resp_1.status, 200)
            mark_resp_1.read()

            conn.request(
                "POST",
                "/publish/mark-for-gom",
                body=json.dumps(
                    {
                        "draft_id": "draft_published",
                        "title": "Published Draft",
                        "prepared_content": "Published payload",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            mark_resp_2 = conn.getresponse()
            self.assertEqual(mark_resp_2.status, 200)
            mark_resp_2.read()

            conn.request(
                "POST",
                "/publish/confirm-gom",
                body=json.dumps(
                    {
                        "draft_id": "draft_published",
                        "published_url": "https://gom.example/posts/published-draft",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            confirm_resp = conn.getresponse()
            self.assertEqual(confirm_resp.status, 200)
            confirm_resp.read()
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
            conn.request("GET", "/publish/gom-queue")
            queue_resp = conn.getresponse()
            queue_body = json.loads(queue_resp.read().decode("utf-8"))

            conn.request("GET", "/publish/published")
            published_resp = conn.getresponse()
            published_body = json.loads(published_resp.read().decode("utf-8"))
            conn.close()

            second_server.shutdown()
            second_server.server_close()
            second_thread.join(timeout=1)

            self.assertEqual(queue_resp.status, 200)
            self.assertEqual(queue_body["count"], 1)
            self.assertEqual(queue_body["items"][0]["draft_id"], "draft_queue")

            self.assertEqual(published_resp.status, 200)
            self.assertEqual(published_body["count"], 1)
            self.assertEqual(published_body["items"][0]["draft_id"], "draft_published")

    def test_persists_ask_idempotency_replay_across_server_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "server-state.json"

            first_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
            first_thread.start()
            time.sleep(0.01)
            first_host, first_port = first_server.server_address

            conn = HTTPConnection(first_host, first_port, timeout=2)
            conn.request(
                "POST",
                "/ask",
                body=json.dumps(
                    {
                        "query": "What should I work on?",
                        "local_confidence": 0.55,
                        "event_id": "evt_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            first_body = json.loads(first_resp.read().decode("utf-8"))
            self.assertEqual(first_resp.status, 200)
            self.assertFalse(first_body["idempotency"]["duplicate"])
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
            conn.request(
                "POST",
                "/ask",
                body=json.dumps(
                    {
                        "query": "Different prompt should be ignored on duplicate",
                        "local_confidence": 0.10,
                        "event_id": "evt_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            second_body = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

            second_server.shutdown()
            second_server.server_close()
            second_thread.join(timeout=1)

            self.assertEqual(second_resp.status, 200)
            self.assertTrue(second_body["idempotency"]["duplicate"])
            self.assertEqual(second_body["answer"]["text"], first_body["answer"]["text"])

    def test_persists_links_apply_idempotency_replay_across_server_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "server-state.json"

            first_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
            first_thread.start()
            time.sleep(0.01)
            first_host, first_port = first_server.server_address

            conn = HTTPConnection(first_host, first_port, timeout=2)
            conn.request(
                "POST",
                "/links/apply",
                body=json.dumps(
                    {
                        "source_note_id": "n1",
                        "links": [{"target_note_id": "n2", "confidence": 0.9}],
                        "event_id": "evt_links_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            first_body = json.loads(first_resp.read().decode("utf-8"))
            self.assertEqual(first_resp.status, 200)
            self.assertFalse(first_body["idempotency"]["duplicate"])
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
            conn.request(
                "POST",
                "/links/apply",
                body=json.dumps(
                    {
                        "source_note_id": "n1",
                        "links": [{"target_note_id": "n3", "confidence": 0.1}],
                        "event_id": "evt_links_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            second_body = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

            second_server.shutdown()
            second_server.server_close()
            second_thread.join(timeout=1)

            self.assertEqual(second_resp.status, 200)
            self.assertTrue(second_body["idempotency"]["duplicate"])
            self.assertEqual(second_body["applied_links"], first_body["applied_links"])

    def test_persists_publish_mark_idempotency_replay_across_server_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "server-state.json"

            first_server = create_server(host="127.0.0.1", port=0, state_file=str(state_file))
            first_thread = threading.Thread(target=first_server.serve_forever, daemon=True)
            first_thread.start()
            time.sleep(0.01)
            first_host, first_port = first_server.server_address

            conn = HTTPConnection(first_host, first_port, timeout=2)
            conn.request(
                "POST",
                "/publish/mark-for-gom",
                body=json.dumps(
                    {
                        "draft_id": "draft_010",
                        "title": "Project Atlas Weekly",
                        "prepared_content": "Ready for export.",
                        "event_id": "evt_publish_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            first_body = json.loads(first_resp.read().decode("utf-8"))
            self.assertEqual(first_resp.status, 200)
            self.assertFalse(first_body["idempotency"]["duplicate"])
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
            conn.request(
                "POST",
                "/publish/mark-for-gom",
                body=json.dumps(
                    {
                        "draft_id": "draft_011",
                        "title": "Different Draft",
                        "prepared_content": "Should be ignored on duplicate event id.",
                        "event_id": "evt_publish_001",
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            second_body = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

            second_server.shutdown()
            second_server.server_close()
            second_thread.join(timeout=1)

            self.assertEqual(second_resp.status, 200)
            self.assertTrue(second_body["idempotency"]["duplicate"])
            self.assertEqual(second_body["draft_id"], first_body["draft_id"])

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

    def test_ask_endpoint_replays_duplicate_event_id(self):
        first_payload = {
            "query": "What should I work on?",
            "local_confidence": 0.55,
            "event_id": "evt_001",
        }
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/ask",
            body=json.dumps(first_payload),
            headers={"Content-Type": "application/json"},
        )
        first_resp = conn.getresponse()
        first_body = json.loads(first_resp.read().decode("utf-8"))
        self.assertEqual(first_resp.status, 200)
        self.assertFalse(first_body["idempotency"]["duplicate"])

        second_payload = {
            "query": "Different prompt should be ignored on duplicate",
            "local_confidence": 0.1,
            "event_id": "evt_001",
        }
        conn.request(
            "POST",
            "/ask",
            body=json.dumps(second_payload),
            headers={"Content-Type": "application/json"},
        )
        second_resp = conn.getresponse()
        second_body = json.loads(second_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(second_resp.status, 200)
        self.assertTrue(second_body["idempotency"]["duplicate"])
        self.assertEqual(second_body["answer"]["text"], first_body["answer"]["text"])

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

    def test_mark_for_gom_replays_duplicate_event_id(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        first_payload = {
            "draft_id": "draft_010",
            "title": "Project Atlas Weekly",
            "prepared_content": "Ready for export.",
            "event_id": "evt_publish_001",
        }
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(first_payload),
            headers={"Content-Type": "application/json"},
        )
        first_resp = conn.getresponse()
        first_body = json.loads(first_resp.read().decode("utf-8"))
        self.assertEqual(first_resp.status, 200)
        self.assertFalse(first_body["idempotency"]["duplicate"])

        second_payload = {
            "draft_id": "draft_011",
            "title": "Different Draft",
            "prepared_content": "Should be ignored on duplicate event id.",
            "event_id": "evt_publish_001",
        }
        conn.request(
            "POST",
            "/publish/mark-for-gom",
            body=json.dumps(second_payload),
            headers={"Content-Type": "application/json"},
        )
        second_resp = conn.getresponse()
        second_body = json.loads(second_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(second_resp.status, 200)
        self.assertTrue(second_body["idempotency"]["duplicate"])
        self.assertEqual(second_body["draft_id"], first_body["draft_id"])

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

    def test_published_list_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        mark_payload = {
            "draft_id": "draft_040",
            "title": "Atlas Journal",
            "prepared_content": "Ready.",
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
            "draft_id": "draft_040",
            "published_url": "https://gom.example/posts/atlas-journal",
        }
        conn.request(
            "POST",
            "/publish/confirm-gom",
            body=json.dumps(confirm_payload),
            headers={"Content-Type": "application/json"},
        )
        confirm_resp = conn.getresponse()
        self.assertEqual(confirm_resp.status, 200)
        confirm_resp.read()

        conn.request("GET", "/publish/published")
        list_resp = conn.getresponse()
        list_body = json.loads(list_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(list_resp.status, 200)
        self.assertEqual(list_body["count"], 1)
        self.assertEqual(list_body["items"][0]["draft_id"], "draft_040")

    def test_organize_classify_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        payload = {
            "notes": [
                {"note_id": "n1", "title": "Project Atlas Weekly Plan"},
                {"note_id": "n2", "title": "Reference Notes: Zettelkasten"},
            ]
        }
        conn.request(
            "POST",
            "/organize/classify",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(len(body["results"]), 2)
        self.assertEqual(body["results"][0]["primary_para"], "project")
        self.assertEqual(body["results"][1]["primary_para"], "resource")

    def test_organize_classify_endpoint_rejects_invalid_payload(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/organize/classify",
            body=json.dumps({"notes": [{"note_id": "n1"}]}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_links_propose_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        payload = {
            "source_note_id": "n1",
            "candidate_notes": [
                {"note_id": "n2", "title": "Atlas Architecture"},
                {"note_id": "n3", "title": "Random Grocery List"},
            ],
        }
        conn.request(
            "POST",
            "/links/propose",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body["source_note_id"], "n1")
        self.assertEqual(len(body["suggestions"]), 2)

    def test_links_propose_endpoint_rejects_empty_candidates(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/links/propose",
            body=json.dumps({"source_note_id": "n1", "candidate_notes": []}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_links_apply_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        payload = {
            "source_note_id": "n1",
            "links": [
                {"target_note_id": "n2", "confidence": 0.88},
                {"target_note_id": "n3", "confidence": 0.79},
            ],
            "min_confidence": 0.8,
        }
        conn.request(
            "POST",
            "/links/apply",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(body["source_note_id"], "n1")
        self.assertEqual(body["applied_count"], 1)

    def test_links_apply_endpoint_rejects_empty_links(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/links/apply",
            body=json.dumps({"source_note_id": "n1", "links": []}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)

    def test_links_apply_endpoint_replays_duplicate_event_id(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        first_payload = {
            "source_note_id": "n1",
            "links": [{"target_note_id": "n2", "confidence": 0.9}],
            "event_id": "evt_links_001",
        }
        conn.request(
            "POST",
            "/links/apply",
            body=json.dumps(first_payload),
            headers={"Content-Type": "application/json"},
        )
        first_resp = conn.getresponse()
        first_body = json.loads(first_resp.read().decode("utf-8"))
        self.assertEqual(first_resp.status, 200)
        self.assertFalse(first_body["idempotency"]["duplicate"])

        second_payload = {
            "source_note_id": "n1",
            "links": [{"target_note_id": "n3", "confidence": 0.1}],
            "event_id": "evt_links_001",
        }
        conn.request(
            "POST",
            "/links/apply",
            body=json.dumps(second_payload),
            headers={"Content-Type": "application/json"},
        )
        second_resp = conn.getresponse()
        second_body = json.loads(second_resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(second_resp.status, 200)
        self.assertTrue(second_body["idempotency"]["duplicate"])
        self.assertEqual(second_body["applied_links"], first_body["applied_links"])

    def test_organize_propose_structure_endpoint(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        payload = {
            "notes": [
                {"note_id": "n1", "title": "Atlas Scratchpad", "folder": "Inbox"},
                {"note_id": "n2", "title": "Atlas Architecture", "folder": "Projects/Atlas"},
            ]
        }
        conn.request(
            "POST",
            "/organize/propose-structure",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 200)
        self.assertEqual(len(body["proposals"]), 2)
        self.assertEqual(body["proposals"][0]["action_mode"], "manual")

    def test_organize_propose_structure_endpoint_rejects_empty_notes(self):
        conn = HTTPConnection(self.host, self.port, timeout=2)
        conn.request(
            "POST",
            "/organize/propose-structure",
            body=json.dumps({"notes": []}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8"))
        conn.close()

        self.assertEqual(resp.status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()

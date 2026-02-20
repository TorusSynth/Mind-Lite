import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from mind_lite.api.service import ApiService


def create_server(host: str = "127.0.0.1", port: int = 8000, state_file: str | None = None) -> ThreadingHTTPServer:
    service = ApiService(state_file=state_file)

    class MindLiteHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed_url = urlsplit(self.path)
            path = parsed_url.path
            query = parse_qs(parsed_url.query)

            if path == "/health":
                self._write_json(200, service.health())
                return

            if path == "/health/ready":
                self._write_json(200, service.health_ready())
                return

            if path == "/metrics":
                self._write_text(200, service.metrics(), "text/plain; version=0.0.4")
                return

            if path == "/runs":
                filters = self._extract_run_filters(query)
                try:
                    runs = service.list_runs(filters)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, runs)
                return

            if path == "/policy/sensitivity":
                self._write_json(200, service.get_sensitivity_policy())
                return

            if path == "/policy/routing":
                self._write_json(200, service.get_routing_policy())
                return

            if path == "/publish/gom-queue":
                self._write_json(200, service.list_gom_queue())
                return

            if path == "/publish/revision-queue":
                self._write_json(200, service.list_revision_queue())
                return

            if path == "/publish/published":
                self._write_json(200, service.list_published())
                return

            if path == "/rag/status":
                self._write_json(200, service.rag_status())
                return

            if path == "/llm/models":
                self._write_json(200, service.llm_list_models())
                return

            if path == "/llm/config":
                self._write_json(200, service.llm_get_config())
                return

            run_route = self._parse_run_route(path)
            if run_route is not None and run_route[1] == "proposals":
                run_id = run_route[0]
                filters = self._extract_proposal_filters(query)
                try:
                    proposals = service.get_run_proposals(run_id, filters)
                except ValueError as exc:
                    error_message = str(exc)
                    status = 404 if "unknown run id" in error_message else 400
                    self._write_json(status, {"error": error_message})
                    return
                self._write_json(200, proposals)
                return

            if run_route is not None and run_route[1] is None:
                run_id = run_route[0]
                try:
                    run = service.get_run(run_id)
                except ValueError as exc:
                    self._write_json(404, {"error": str(exc)})
                    return
                self._write_json(200, run)
                return

            self._write_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            body = self._read_json_body()
            if body is None:
                self._write_json(400, {"error": "invalid json"})
                return

            if path == "/onboarding/analyze-folder":
                try:
                    result = service.analyze_folder(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return

                self._write_json(200, result)
                return

            if path == "/onboarding/analyze-folders":
                try:
                    result = service.analyze_folders(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return

                self._write_json(200, result)
                return

            if path == "/policy/sensitivity/check":
                try:
                    result = service.check_sensitivity(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/ask":
                try:
                    result = service.ask(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/score":
                try:
                    result = service.publish_score(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/prepare":
                try:
                    result = service.publish_prepare(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/mark-for-gom":
                try:
                    result = service.mark_for_gom(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/mark-for-revision":
                try:
                    result = service.mark_for_revision(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/export-for-gom":
                try:
                    result = service.export_for_gom(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/publish/confirm-gom":
                try:
                    result = service.confirm_gom(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/organize/classify":
                try:
                    result = service.organize_classify(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/organize/propose-structure":
                try:
                    result = service.organize_propose_structure(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/links/propose":
                try:
                    result = service.links_propose(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/links/apply":
                try:
                    result = service.links_apply(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/rag/index-vault":
                try:
                    result = service.rag_index_vault(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/rag/index-folder":
                try:
                    result = service.rag_index_folder(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/rag/retrieve":
                try:
                    result = service.rag_retrieve(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/llm/config":
                try:
                    result = service.llm_set_config(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            if path == "/llm/config/api-key":
                try:
                    result = service.llm_set_api_key(body)
                except ValueError as exc:
                    self._write_json(400, {"error": str(exc)})
                    return
                self._write_json(200, result)
                return

            run_route = self._parse_run_route(path)
            if run_route is not None and run_route[1] == "apply":
                run_id = run_route[0]
                try:
                    result = service.apply_run(run_id, body)
                except ValueError as exc:
                    error_message = str(exc)
                    status = 404 if "unknown run id" in error_message else 400
                    self._write_json(status, {"error": error_message})
                    return
                self._write_json(200, result)
                return

            if run_route is not None and run_route[1] == "approve":
                run_id = run_route[0]
                try:
                    result = service.approve_run(run_id, body)
                except ValueError as exc:
                    error_message = str(exc)
                    status = 404 if "unknown run id" in error_message else 400
                    self._write_json(status, {"error": error_message})
                    return
                self._write_json(200, result)
                return

            if run_route is not None and run_route[1] == "rollback":
                run_id = run_route[0]
                try:
                    result = service.rollback_run(run_id, body)
                except ValueError as exc:
                    error_message = str(exc)
                    status = 404 if "unknown run id" in error_message else 400
                    self._write_json(status, {"error": error_message})
                    return
                self._write_json(200, result)
                return

            self._write_json(404, {"error": "not found"})

        def do_DELETE(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]

            if path == "/llm/config/api-key":
                result = service.llm_clear_api_key()
                self._write_json(200, result)
                return

            self._write_json(404, {"error": "not found"})

        def _parse_run_route(self, path: str) -> tuple[str, str | None] | None:
            parts = path.split("/")
            if len(parts) == 3 and parts[1] == "runs" and parts[2]:
                return parts[2], None
            if len(parts) == 4 and parts[1] == "runs" and parts[2] and parts[3]:
                return parts[2], parts[3]
            return None

        def _extract_proposal_filters(self, query: dict[str, list[str]]) -> dict:
            filters = {}
            for key in ("risk_tier", "action_mode", "status"):
                values = query.get(key)
                if not values:
                    continue
                filters[key] = values[-1]
            return filters

        def _extract_run_filters(self, query: dict[str, list[str]]) -> dict:
            filters = {}
            values = query.get("state")
            if values:
                filters["state"] = values[-1]
            return filters

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _read_json_body(self) -> dict | None:
            try:
                content_len = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            raw = self.rfile.read(content_len)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            if not isinstance(parsed, dict):
                return None
            return parsed

        def _write_json(self, status_code: int, payload: dict) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _write_text(self, status_code: int, payload: str, content_type: str) -> None:
            encoded = payload.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return ThreadingHTTPServer((host, port), MindLiteHandler)

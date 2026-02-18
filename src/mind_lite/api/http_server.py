import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mind_lite.api.service import ApiService


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    service = ApiService()

    class MindLiteHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._write_json(200, service.health())
                return

            if self.path.startswith("/runs/"):
                run_id = self.path.removeprefix("/runs/")
                try:
                    run = service.get_run(run_id)
                except ValueError as exc:
                    self._write_json(404, {"error": str(exc)})
                    return
                self._write_json(200, run)
                return

            self._write_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/onboarding/analyze-folder":
                self._write_json(404, {"error": "not found"})
                return

            body = self._read_json_body()
            if body is None:
                self._write_json(400, {"error": "invalid json"})
                return

            try:
                result = service.analyze_folder(body)
            except ValueError as exc:
                self._write_json(400, {"error": str(exc)})
                return

            self._write_json(200, result)

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

    return ThreadingHTTPServer((host, port), MindLiteHandler)

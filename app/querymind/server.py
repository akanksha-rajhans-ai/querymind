"""Small standard-library HTTP server for the local MVP demo."""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.querymind.engine import QueryMindEngine


ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "app" / "web"


class QueryMindHandler(BaseHTTPRequestHandler):
    engine = QueryMindEngine()

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/schema":
            self._send_json(self.engine.schema_summary())
            return
        if parsed.path == "/api/examples":
            self._send_json({"examples": self.engine.example_questions()})
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        if parsed.path != "/api/query":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            result = self.engine.ask(str(payload.get("question", "")))
            self._send_json(
                {
                    "question": result.question,
                    "sql": result.sql,
                    "columns": result.columns,
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "rationale": result.rationale,
                    "confidence": result.confidence,
                    "latency_ms": result.latency_ms,
                    "retrieved_tables": [
                        {
                            "table": table.table,
                            "score": table.score,
                            "matched_terms": table.matched_terms,
                        }
                        for table in result.retrieved_tables
                    ],
                }
            )
        except Exception as exc:  # noqa: BLE001 - API should return useful errors
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[QueryMind] {self.address_string()} - {format % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path.lstrip("/"))
        target = (WEB_DIR / relative).resolve()
        try:
            target.relative_to(WEB_DIR.resolve())
        except ValueError:
            self._send_json({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run_server(host: str | None = None, port: int | None = None) -> None:
    host = host or os.getenv("QUERYMIND_HOST", "127.0.0.1")
    port = port or int(os.getenv("QUERYMIND_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), QueryMindHandler)
    print(f"QueryMind running at http://{host}:{port}")
    server.serve_forever()


"""The job ids of a queue's uncollected results, read through every page."""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from atrium.synthesize.pending_worker_jobs import pending_worker_jobs


def serve(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    asked: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            asked.append(self.path)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            after, limit = int(query["after"][0]), int(query["limit"][0])
            page = [row for row in rows if row["seq"] > after][:limit]
            data = json.dumps({"results": page}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", asked


def test_every_page_is_read(monkeypatch, tmp_path):
    rows = [
        {"seq": n, "job_id": f"j{n}", "result_id": f"r{n}", "control": None} for n in range(1, 251)
    ]
    url, asked = serve(rows)
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_URL", url)
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
    assert pending_worker_jobs("atrium.synthesis") == {f"j{n}" for n in range(1, 251)}
    assert len(asked) == 3
    assert all("queue=atrium.synthesis" in path for path in asked)

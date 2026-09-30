import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.worker_http_call import worker_http_call
from atrium.synthesize.worker_lane_call import worker_lane_call

TOOL = {"input_schema": {"type": "object", "properties": {"title": {"type": "string"}}}}


def refusing(monkeypatch, tmp_path, status: int, body: bytes) -> list[str]:
    """Serve a coordinator that refuses every POST with ``status`` and ``body``."""
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            seen.append("POST " + self.path)
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            seen.append("GET " + self.path)
            self.send_response(500)
            self.end_headers()

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
    monkeypatch.setenv("ATRIUM_WORKER_URL", f"http://127.0.0.1:{server.server_address[1]}")
    return seen


def test_a_full_queue_stops_the_pass_instead_of_failing_the_conversation(monkeypatch, tmp_path):
    seen = refusing(monkeypatch, tmp_path, 429, json.dumps({"error": "outstanding_limit"}).encode())
    with pytest.raises(QuotaExhaustedError, match=r"queue full \(outstanding_limit\)") as caught:
        worker_lane_call(LanePrompt("s", "u"), TOOL)
    # The tick script switches lanes on "cooling until"; a full queue is not that.
    assert "cooling until" not in str(caught.value)
    assert seen == ["POST /v1/jobs"]


def test_an_oversized_body_names_itself(monkeypatch, tmp_path):
    refusing(monkeypatch, tmp_path, 413, json.dumps({"error": "payload_too_large"}).encode())
    with pytest.raises(RuntimeError, match=r"too large \(payload_too_large\)") as caught:
        worker_http_call("POST", "/v1/jobs", {"prompt": "x"})
    assert not isinstance(caught.value, QuotaExhaustedError)


def test_an_untrusted_body_never_reaches_the_message(monkeypatch, tmp_path):
    refusing(monkeypatch, tmp_path, 400, b'{"error": "secret prompt text here"}')
    with pytest.raises(RuntimeError, match=r"^worker answered HTTP 400 \(unknown\)$"):
        worker_http_call("POST", "/v1/jobs", {"prompt": "x"})

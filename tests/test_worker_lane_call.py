import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import local_lane_call
from atrium.synthesize.worker_lane_call import worker_lane_call

TOOL = {
    "input_schema": {
        "type": "object",
        "required": ["title"],
        "properties": {"title": {"type": "string"}},
    }
}


def serve(results: list[Any], state: str = "succeeded") -> tuple[str, dict[str, Any]]:
    seen: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length) or b"{}")
            seen.setdefault(self.path, []).append(body)
            if self.path == "/v1/jobs":
                self._reply(201, {"id": "j1", "created": True})
            else:
                self._reply(200, {"acked": True})

        def do_GET(self) -> None:
            self._reply(200, {"id": "j1", "state": state, "error": None, "result": results.pop(0)})

        def _reply(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", seen


def configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Any, url: str) -> None:
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_URL", url)
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
    monkeypatch.setenv("ATRIUM_WORKER_POLL", "0")


def test_submits_personal_job_waits_and_acks(monkeypatch, tmp_path):
    usage = {"tokens_in": 5, "tokens_out": 2}
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": usage,
    }
    url, seen = serve([ok])
    configure(monkeypatch, tmp_path, url)
    out = worker_lane_call(LanePrompt("sys", "user"), TOOL, "qwen3.6:35b")
    assert out == {
        "input": {"title": "t"},
        "model": "qwen3.6:35b",
        "usage": {"input_tokens": 5, "output_tokens": 2},
    }
    job = seen["/v1/jobs"][0]
    assert (job["privacy"], job["queue"], job["requirements"]["models"]) == (
        "personal",
        "atrium.synthesis",
        ["qwen3.6:35b"],
    )
    assert seen["/v1/jobs/j1/ack"][0] == {"result_id": "r1", "decline": False}


def test_a_split_request_is_declined_and_waiting_continues(monkeypatch, tmp_path):
    split = {"result_id": "r0", "control": "split_requested", "output": None, "usage": None}
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
    }
    url, seen = serve([split, ok])
    configure(monkeypatch, tmp_path, url)
    worker_lane_call(LanePrompt("sys", "user"), TOOL)
    assert seen["/v1/jobs/j1/ack"][0] == {"result_id": "r0", "decline": True}


@pytest.mark.parametrize(
    "state", ["succeeded", "failed", "cancelled", "expired", "unacked_expired", "superseded"]
)
def test_an_already_consumed_job_fails_fast(monkeypatch, tmp_path, state):
    url, _ = serve([None], state=state)
    configure(monkeypatch, tmp_path, url)
    with pytest.raises(RuntimeError, match="worker job already consumed"):
        worker_lane_call(LanePrompt("sys", "user"), TOOL)


def test_worker_prompt_equals_the_local_lane_prompt(monkeypatch, tmp_path):
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
    }
    url, seen = serve([ok])
    configure(monkeypatch, tmp_path, url)
    parts = LanePrompt("sys", "user body")
    worker_lane_call(parts, TOOL)
    sent: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def read(self, *args: Any) -> bytes:
            return json.dumps({"message": {"content": '{"title": "t"}'}}).encode()

    def fake_urlopen(request: Any, timeout: float) -> Response:
        sent.update(json.loads(request.data))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    local_lane_call(parts, TOOL)
    worker_prompt = seen["/v1/jobs"][0]["input"]["messages"][0]["content"]
    assert worker_prompt == sent["messages"][0]["content"]

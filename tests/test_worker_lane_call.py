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


def serve(
    results: list[Any], state: str = "succeeded", consumed: int = 0
) -> tuple[str, dict[str, Any]]:
    seen: dict[str, Any] = {}
    polled: set[int] = set()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length) or b"{}")
            seen.setdefault(self.path, []).append(body)
            if self.path == "/v1/jobs":
                self._reply(201, {"id": f"j{len(seen['/v1/jobs'])}", "created": True})
            else:
                self._reply(200, {"acked": True})

        def do_GET(self) -> None:
            number = int(self.path.rsplit("/", 1)[1][1:])
            if number <= consumed:
                self._reply(200, {"id": f"j{number}", "state": state, "result": None})
            elif number not in polled:
                polled.add(number)
                self._reply(200, {"id": f"j{number}", "state": "queued", "result": None})
            else:
                self._reply(200, {"id": f"j{number}", "state": "running", "result": results.pop(0)})

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


def test_submits_personal_job_and_returns_the_result_unacked(monkeypatch, tmp_path):
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
        "model": "unknown",
        "usage": {"input_tokens": 5, "output_tokens": 2},
        "worker_results": [{"job_id": "j1", "result_id": "r1"}],
    }
    job = seen["/v1/jobs"][0]
    assert (job["privacy"], job["queue"], job["requirements"]["models"]) == (
        "personal",
        "atrium.synthesis",
        ["qwen3.6:35b"],
    )
    # The caller acks after its registry write, not the lane.
    assert "/v1/jobs/j1/ack" not in seen


def test_the_record_names_the_executor_that_answered(monkeypatch, tmp_path):
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
        "executor": {"node": "n", "provider": "openrouter", "model": "qwen/qwen3.8-27b:free"},
    }
    url, _ = serve([ok])
    configure(monkeypatch, tmp_path, url)
    out = worker_lane_call(LanePrompt("sys", "user"), TOOL, "qwen3.6:35b")
    assert out["model"] == "openrouter-qwen/qwen3.8-27b:free"


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
def test_a_consumed_base_key_walks_to_the_next_suffix(monkeypatch, tmp_path, state):
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
    }
    url, seen = serve([ok, ok], state=state, consumed=1)
    configure(monkeypatch, tmp_path, url)
    out = worker_lane_call(LanePrompt("sys", "user"), TOOL)
    keys = [job["idempotency_key"] for job in seen["/v1/jobs"]]
    assert len(keys) == 2
    assert keys[1] == keys[0] + ":r1"
    assert out["worker_results"] == [{"job_id": "j2", "result_id": "r1"}]


def test_four_failed_keys_end_in_retries_exhausted(monkeypatch, tmp_path):
    url, seen = serve([], state="failed", consumed=99)
    configure(monkeypatch, tmp_path, url)
    with pytest.raises(RuntimeError, match="worker job retries exhausted"):
        worker_lane_call(LanePrompt("sys", "user"), TOOL)
    assert len(seen["/v1/jobs"]) == 4


def test_successes_another_caller_consumed_spend_no_failure_budget(monkeypatch, tmp_path):
    """Identical chunk text in other conversations spent four keys on 2026-10-09."""
    ok = {
        "result_id": "r5",
        "control": None,
        "output": {"json": {"title": "t"}},
        "usage": {},
    }
    url, seen = serve([ok, ok], consumed=4)
    configure(monkeypatch, tmp_path, url)
    out = worker_lane_call(LanePrompt("sys", "user"), TOOL)
    assert out["input"] == {"title": "t"}
    assert seen["/v1/jobs"][-1]["idempotency_key"].endswith(":r4")


def test_consumed_successes_still_end_after_eight_keys(monkeypatch, tmp_path):
    url, seen = serve([], consumed=99)
    configure(monkeypatch, tmp_path, url)
    with pytest.raises(RuntimeError, match="worker job retries exhausted"):
        worker_lane_call(LanePrompt("sys", "user"), TOOL)
    assert len(seen["/v1/jobs"]) == 8


def test_a_first_key_success_submits_once(monkeypatch, tmp_path):
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
    }
    url, seen = serve([ok, ok])
    configure(monkeypatch, tmp_path, url)
    worker_lane_call(LanePrompt("sys", "user"), TOOL)
    assert len(seen["/v1/jobs"]) == 1


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


def test_the_submitted_job_id_is_reported_before_waiting(monkeypatch, tmp_path):
    ok = {
        "result_id": "r1",
        "control": None,
        "output": {"text": "{}", "json": {"title": "t"}},
        "usage": {},
    }
    url, _seen = serve([ok])
    configure(monkeypatch, tmp_path, url)
    submitted: list[str] = []
    worker_lane_call(LanePrompt("sys", "user"), TOOL, on_submit=submitted.append)
    assert submitted == ["j1"]

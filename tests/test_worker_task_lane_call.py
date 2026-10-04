import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.lane_prompt_text import lane_prompt_text
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.worker_task_lane_call import worker_task_lane_call
from atrium.synthesize.worker_task_lane_model_id import worker_task_lane_model_id

TOOL = {
    "input_schema": {
        "type": "object",
        "required": ["title"],
        "properties": {"title": {"type": "string"}},
    }
}


def serve(states: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """A coordinator whose job answers ``states`` in order, the last one forever."""
    seen: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            seen.setdefault(self.path, []).append(json.loads(self.rfile.read(length) or b"{}"))
            if self.path == "/v1/jobs":
                self._reply({"id": "j1", "created": True})
            else:
                self._reply({"acked": True})

        def do_GET(self) -> None:
            state = states.pop(0) if len(states) > 1 else states[0]
            self._reply({"id": "j1", "error": None, **state})

        def _reply(self, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", seen


@pytest.fixture
def coordinator(monkeypatch, tmp_path):
    def start(states: list[dict[str, Any]]) -> dict[str, Any]:
        url, seen = serve(states)
        token = tmp_path / "atrium.token"
        token.write_text("tok")
        monkeypatch.setenv("ATRIUM_WORKER_URL", url)
        monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
        monkeypatch.setenv("ATRIUM_WORKER_POLL", "0")
        return seen

    return start


QUEUED = {"state": "queued", "result": None, "cooling_until": None}
DONE = {
    "state": "succeeded",
    "cooling_until": None,
    "result": {
        "result_id": "r1",
        "control": None,
        "detail": None,
        "output": {"text": '{"title": "t"}', "json": {"title": "t"}},
        "executor": {"node": "n", "provider": "agy", "model": ""},
        "usage": None,
    },
}


def test_submits_a_personal_task_and_returns_its_answer_unacked(coordinator):
    seen = coordinator([QUEUED, DONE])
    parts = LanePrompt("sys", "user")
    out = worker_task_lane_call(parts, TOOL)
    assert out == {
        "input": {"title": "t"},
        "model": "agy",
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "worker_results": [{"job_id": "j1", "result_id": "r1"}],
    }
    job = seen["/v1/jobs"][0]
    assert (job["kind"], job["queue"], job["privacy"]) == ("task", "atrium.tasks", "personal")
    schema = {**TOOL["input_schema"], "additionalProperties": False}
    assert job["input"] == {
        "profile": "atrium.agy",
        "prompt": lane_prompt_text(parts, schema),
        "output_schema": schema,
    }
    assert job["idempotency_key"].startswith("task:")
    # The caller acks after its registry write, not the lane.
    assert "/v1/jobs/j1/ack" not in seen


def test_the_resolved_model_names_runner_and_model(coordinator):
    done = json.loads(json.dumps(DONE))
    done["result"]["executor"] = {
        "node": "n",
        "provider": "agy",
        "model": "gemini-3.7-flash-medium",
    }
    coordinator([done])
    assert (
        worker_task_lane_call(LanePrompt("s", "u"), TOOL)["model"] == "agy-gemini-3.7-flash-medium"
    )


def test_every_runner_resting_stops_the_pass_without_an_ack(coordinator):
    seen = coordinator([{**QUEUED, "cooling_until": 1_900_000_000.5}])
    with pytest.raises(QuotaExhaustedError, match="cooling until 1900000000"):
        worker_task_lane_call(LanePrompt("s", "u"), TOOL)
    assert "/v1/jobs/j1/ack" not in seen


def test_a_failed_task_is_acked_and_raised_with_its_code(coordinator):
    failed = {
        "state": "failed",
        "cooling_until": None,
        "result": {"result_id": "r2", "control": "failed", "detail": {"error": "timeout"}},
    }
    seen = coordinator([failed])
    with pytest.raises(RuntimeError, match=r"failed \(timeout\)"):
        worker_task_lane_call(LanePrompt("s", "u"), TOOL)
    assert seen["/v1/jobs/j1/ack"] == [{"result_id": "r2", "decline": False}]


def test_an_oversized_prompt_is_refused_before_submitting(coordinator):
    seen = coordinator([QUEUED])
    with pytest.raises(RuntimeError, match="too large"):
        worker_task_lane_call(LanePrompt("s", "x" * (600 * 1024)), TOOL)
    assert "/v1/jobs" not in seen


def test_the_population_is_named_after_the_profile():
    assert worker_task_lane_model_id("atrium.agy") == "worker-atrium.agy"


def test_the_submitted_task_id_is_reported_before_waiting(coordinator):
    coordinator([QUEUED, DONE])
    submitted: list[str] = []
    worker_task_lane_call(LanePrompt("sys", "user"), TOOL, on_submit=submitted.append)
    assert submitted == ["j1"]

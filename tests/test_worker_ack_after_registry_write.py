"""A worker result is acked only after the registry holds it, and a crash in between loses nothing."""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from atrium.synthesize.ack_recorded_worker_results import ack_recorded_worker_results
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.read_records import read_records
from atrium.synthesize.synthesize_conversation import synthesize_conversation
from atrium.synthesize.worker_task_lane_call import WORKER_TASK_QUEUE, worker_task_lane_call

OUTPUT = {"title": "Cache TTL", "summary": "Expiry is by TTL.", "facts": [], "open_ends": []}


class Coordinator:
    """One job per idempotency key, each finishing with one result that stays offered until acked."""

    def __init__(self) -> None:
        self.jobs: dict[str, str] = {}
        self.acked: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def unacked(self) -> list[dict[str, Any]]:
        done = {ack["result_id"] for ack in self.acked}
        return [
            {"seq": n, "job_id": job_id, "result_id": f"r-{job_id}", "control": None}
            for n, job_id in enumerate(sorted(self.jobs.values()), start=1)
            if f"r-{job_id}" not in done
        ]


def serve(coordinator: Coordinator) -> str:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            with coordinator.lock:
                if self.path == "/v1/jobs":
                    key = body["idempotency_key"]
                    job_id = coordinator.jobs.setdefault(key, f"j{len(coordinator.jobs) + 1}")
                    self._reply({"id": job_id})
                else:
                    coordinator.acked.append({"path": self.path, **body})
                    self._reply({"acked": True})

        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            with coordinator.lock:
                pending = coordinator.unacked()
            if url.path == "/v1/results":
                assert urllib.parse.parse_qs(url.query)["queue"] == [WORKER_TASK_QUEUE]
                self._reply({"results": pending})
                return
            job_id = url.path.rsplit("/", 1)[1]
            row = next((r for r in pending if r["job_id"] == job_id), None)
            result = None
            if row is not None:
                result = {
                    "result_id": row["result_id"],
                    "control": None,
                    "output": {"text": json.dumps(OUTPUT), "json": OUTPUT},
                    "executor": {"provider": "agy", "model": ""},
                    "usage": {"tokens_in": 1, "tokens_out": 1},
                }
            self._reply(
                {"id": job_id, "state": "succeeded", "cooling_until": None, "result": result}
            )

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
    return f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture
def coordinator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Coordinator:
    state = Coordinator()
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_URL", serve(state))
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))
    monkeypatch.setenv("ATRIUM_WORKER_POLL", "0")
    return state


def _conversation() -> dict[str, Any]:
    return {
        "id": "c" * 64,
        "source": "claude-code",
        "schemaVersion": 2,
        "provenance": {"contentSha256": "a" * 64},
        "startedAt": "2026-09-04T10:00:00Z",
        "events": [
            {"id": "e1", "kind": "message", "role": "user", "text": "how does the cache expire"},
            {"id": "e2", "kind": "message", "role": "assistant", "text": "by TTL, checked on read"},
        ],
    }


def _producer(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
    return worker_task_lane_call(LanePrompt(system_text, user_text), tool)


def _next_pass(registry: Path) -> dict[str, Any]:
    """What `atrium synthesize --producer task` does: drain recorded results, then synthesize."""
    records = list(read_records(registry))
    recorded = {r["result_id"] for record in records for r in record.get("worker_results") or []}
    acked = ack_recorded_worker_results(WORKER_TASK_QUEUE, recorded)
    done = {record["episode_id"] for record in records}
    counts = synthesize_conversation(_conversation(), _producer, "worker-x", registry, done)
    return {**counts, "drained": acked}


class _CrashError(Exception):
    pass


def test_the_ack_follows_the_registry_write(coordinator, tmp_path):
    registry = tmp_path / "registry"
    counts = synthesize_conversation(_conversation(), _producer, "worker-x", registry)
    assert counts["synthesized"] == 1
    [record] = read_records(registry)
    assert record["worker_results"] == [{"job_id": "j1", "result_id": "r-j1"}]
    assert coordinator.acked == [{"path": "/v1/jobs/j1/ack", "result_id": "r-j1", "decline": False}]


def test_a_crash_between_registry_write_and_ack_is_settled_by_the_next_pass(
    coordinator, tmp_path, monkeypatch
):
    registry = tmp_path / "registry"

    def crash(_results: list[dict[str, Any]]) -> None:
        raise _CrashError

    with monkeypatch.context() as patch:
        patch.setattr("atrium.synthesize.synthesize_conversation.ack_worker_results", crash)
        with pytest.raises(_CrashError):
            synthesize_conversation(_conversation(), _producer, "worker-x", registry)
    # The crash window: the record is on disk, the worker still offers the result.
    assert len(list(read_records(registry))) == 1
    assert coordinator.acked == []
    assert [r["result_id"] for r in coordinator.unacked()] == ["r-j1"]

    counts = _next_pass(registry)

    assert counts == {"synthesized": 0, "skipped": 1, "trivial": 0, "drained": 1}
    assert len(list((registry / "records").glob("*.json"))) == 1
    assert coordinator.acked == [{"path": "/v1/jobs/j1/ack", "result_id": "r-j1", "decline": False}]
    assert coordinator.unacked() == []
    assert len(coordinator.jobs) == 1

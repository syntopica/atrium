"""A pass collects the worker results earlier passes left behind before it submits anything new.

A pass that stops waiting on a job (its wait budget, a timeout kill, a later
chunk refused) leaves the result to arrive unacknowledged. Later passes walk
the newest conversations first and stop at the first full-queue refusal, so
without help they never reach the conversation that result belongs to, and
uncollected results fill the queue until nothing new is admitted.
"""

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from atrium.cli import main
from atrium.synthesize import synthesize_conversation as synthesize_module
from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.read_worker_submissions import read_worker_submissions
from atrium.synthesize.record_worker_submission import record_worker_submission
from atrium.synthesize.write_record import write_record

OUTPUT = {"title": "t", "summary": "s", "facts": [], "open_ends": []}


def serve(pending: list[str]) -> str:
    """A coordinator offering one uncollected result per job id in ``pending``."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            self._reply({"id": "j-new", "created": True} if self.path == "/v1/jobs" else {})

        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            if url.path == "/v1/results":
                after = int(urllib.parse.parse_qs(url.query)["after"][0])
                rows = [
                    {"seq": n, "job_id": job, "result_id": f"r-{job}", "control": None}
                    for n, job in enumerate(pending, start=1)
                    if n > after
                ]
                self._reply({"results": rows})
                return
            job = url.path.rsplit("/", 1)[1]
            result = {
                "result_id": f"r-{job}",
                "control": None,
                "output": {"json": OUTPUT},
                "usage": {},
            }
            self._reply({"id": job, "state": "succeeded", "result": result})

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


def _events() -> list[dict[str, Any]]:
    return [
        {"id": "e1", "kind": "message", "role": "user", "text": "how does the cache expire"},
        {"id": "e2", "kind": "message", "role": "assistant", "text": "by TTL"},
    ]


def _archive(tmp_path, names: list[str]):
    archive = tmp_path / "archive.jsonl"
    lines: list[dict[str, Any]] = [{"kind": "rocket-agents-conversation-export"}]
    lines += [
        {"id": name, "updatedAt": f"2026-09-{30 - n:02d}", "events": _events()}
        for n, name in enumerate(names)
    ]
    archive.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return archive


@pytest.fixture
def worker(monkeypatch, tmp_path):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    monkeypatch.setenv("ATRIUM_LOCAL_TRANSPORT", "worker")
    monkeypatch.setenv("ATRIUM_WORKER_POLL", "0")
    token = tmp_path / "atrium.token"
    token.write_text("tok")
    monkeypatch.setenv("ATRIUM_WORKER_TOKEN_FILE", str(token))

    def start(pending: list[str]):
        monkeypatch.setenv("ATRIUM_WORKER_URL", serve(pending))
        return state / "synthesis"

    return start


def _pass(tmp_path, names: list[str]) -> int:
    archive = _archive(tmp_path, names)
    return main(["synthesize", str(archive), "--producer", "local", "--workers", "1"])


def _last_pass(registry) -> dict[str, Any]:
    status = registry.parent / "status" / "synthesis.json"
    return json.loads(status.read_text())["lastPass"]


def test_conversations_holding_uncollected_results_are_walked_first(worker, tmp_path, monkeypatch):
    registry = worker(["j-old"])
    record_worker_submission(registry / "worker-submissions.jsonl", "j-old", "conv-old")
    walked: list[str] = []

    def fake(conversation, *args, **kwargs):
        walked.append(conversation["id"])
        return {"synthesized": 1, "skipped": 0}

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", fake)
    assert _pass(tmp_path, ["conv-new", "conv-mid", "conv-old"]) == 0
    assert walked == ["conv-old", "conv-new", "conv-mid"]


def test_a_full_queue_does_not_stop_collecting_the_other_held_results(
    worker, tmp_path, monkeypatch
):
    registry = worker(["j-a", "j-b"])
    journal = registry / "worker-submissions.jsonl"
    record_worker_submission(journal, "j-a", "conv-a")
    record_worker_submission(journal, "j-b", "conv-b")
    walked: list[str] = []

    def fake(conversation, *args, **kwargs):
        walked.append(conversation["id"])
        if conversation["id"] in {"conv-a", "conv-new"}:
            raise QuotaExhaustedError("worker queue full (outstanding_limit)")
        return {"synthesized": 1, "skipped": 0}

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", fake)
    assert _pass(tmp_path, ["conv-new", "conv-a", "conv-b", "conv-z"]) == 0
    # conv-z is behind the wall conv-new hit; conv-b still had its result collected.
    assert walked == ["conv-a", "conv-b", "conv-new"]
    assert _last_pass(registry)["synthesized"] == 1


def test_every_submission_is_journaled_against_its_conversation(worker, tmp_path):
    registry = worker([])
    assert _pass(tmp_path, ["conv-a"]) == 0
    assert read_worker_submissions(registry / "worker-submissions.jsonl") == {"j-new": "conv-a"}
    assert _last_pass(registry)["synthesized"] == 1


def test_deferred_counts_only_conversations_with_work_left(worker, tmp_path, monkeypatch):
    registry = worker([])
    done_id = episode_identity("conv-done", ["e1", "e2"])
    record = {"job_key": "k-done", "episode_id": done_id, "conversation_id": "conv-done"}
    write_record(registry, "k-done", {**record, "revision_sha256": ""})
    original = synthesize_module.synthesize_conversation

    def fake(conversation, *args, **kwargs):
        if conversation["id"] == "conv-wall":
            raise QuotaExhaustedError("worker queue full (outstanding_limit)")
        return original(conversation, *args, **kwargs)

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", fake)
    assert _pass(tmp_path, ["conv-wall", "conv-done", "conv-todo"]) == 0
    last = _last_pass(registry)
    # conv-wall hit the wall and conv-todo has no record at its revision; conv-done has one.
    assert (last["deferred"], last["skipped"], last["synthesized"]) == (2, 1, 0)

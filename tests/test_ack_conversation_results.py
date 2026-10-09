"""A holding conversation with nothing left to make releases what it holds.

Walking such a conversation re-submits nothing, so its offered results held
queue slots until the worker expired them; 16 conversations were in that state
on 2026-10-09.
"""

from typing import Any

from atrium.synthesize import ack_conversation_results as module
from atrium.synthesize.ack_conversation_results import ack_conversation_results


def test_only_results_no_other_conversation_submitted_are_acked_across_pages(monkeypatch):
    rows = [{"seq": n, "job_id": f"j{n}", "result_id": f"r{n}"} for n in range(1, 151)]
    owners = {"j3": {"mine"}, "j120": {"mine"}, "j4": {"other"}, "j5": {"mine", "other"}}

    def call(method: str, path: str, payload: Any = None) -> Any:
        after = int(path.split("after=")[1].split("&", maxsplit=1)[0])
        return {"results": [row for row in rows if row["seq"] > after][:100]}

    acked: list[dict] = []
    monkeypatch.setattr(module, "worker_http_call", call)
    monkeypatch.setattr(module, "ack_worker_results", acked.extend)
    assert ack_conversation_results("atrium.synthesis", "mine", owners) == 2
    assert [row["job_id"] for row in acked] == ["j3", "j120"]


def test_an_unjournaled_conversation_acks_nothing(monkeypatch):
    monkeypatch.setattr(
        module,
        "worker_http_call",
        lambda *args: {"results": [{"seq": 1, "job_id": "j1", "result_id": "r1"}]},
    )
    acked: list[dict] = []
    monkeypatch.setattr(module, "ack_worker_results", acked.extend)
    assert ack_conversation_results("atrium.synthesis", "mine", {}) == 0
    assert acked == []

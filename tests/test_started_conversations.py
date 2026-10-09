"""A conversation that stops half done is remembered, and its kept work reused.

Once map chunks are kept and acked at once, a conversation stopped between
its chunks and its record holds no worker result, so nothing told the next
pass to resume it first. A started marker does, and the kept partials mean the
resume pays only for what was not yet made.
"""

import os
import time
from pathlib import Path

import pytest

from atrium.synthesize import kept_chunk_synthesis as kept_module
from atrium.synthesize import synthesize_conversation as conversation_module
from atrium.synthesize.prune_partials import MAX_AGE_SECONDS, prune_partials
from atrium.synthesize.started_conversations import started_conversations
from atrium.synthesize.started_marker import started_marker
from atrium.synthesize.synthesize_conversation import synthesize_conversation

CONVERSATION = {
    "id": "conversation-1",
    "events": [
        {
            "id": str(index),
            "role": "user" if index % 2 == 0 else "assistant",
            "text": f"turn {index}",
        }
        for index in range(4)
    ],
}


class _Producer:
    """Answers every call, or fails on the call numbered ``fail_on``."""

    def __init__(self, fail_on: int | None = None) -> None:
        self.calls = 0
        self.fail_on = fail_on

    def __call__(self, system_text, user_text, tool):
        self.calls += 1
        if self.calls == self.fail_on:
            raise RuntimeError("producer stopped")
        return {
            "input": {"title": f"t{self.calls}", "summary": "s"},
            "model": "m",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "worker_results": [],
        }


@pytest.fixture(autouse=True)
def _no_worker(monkeypatch):
    monkeypatch.setattr(kept_module, "ack_worker_results", lambda results: None)
    monkeypatch.setattr(conversation_module, "ack_worker_results", lambda results: None)


@pytest.fixture
def two_chunk_episode(monkeypatch):
    """One episode cut into two map chunks, so a run makes three calls."""
    episode = {"event_indexes": [0, 1, 2, 3], "chunks": [[0, 1], [2, 3]]}
    monkeypatch.setattr(conversation_module, "segment_episodes", lambda events: [episode])


def test_a_failed_reduce_leaves_the_mark_and_the_resume_pays_only_for_it(
    tmp_path: Path, two_chunk_episode
):
    with pytest.raises(RuntimeError):
        synthesize_conversation(CONVERSATION, _Producer(fail_on=3), "model", tmp_path)
    assert started_conversations(tmp_path / "partials") == {"conversation-1"}

    resumed = _Producer()
    result = synthesize_conversation(CONVERSATION, resumed, "model", tmp_path)
    assert result["synthesized"] == 1
    assert resumed.calls == 1  # the reduce; both map chunks came from disk
    assert started_conversations(tmp_path / "partials") == set()


def test_a_finished_conversation_leaves_no_mark(tmp_path: Path, two_chunk_episode):
    synthesize_conversation(CONVERSATION, _Producer(), "model", tmp_path)
    assert started_conversations(tmp_path / "partials") == set()


def test_a_conversation_with_nothing_to_make_is_never_marked(tmp_path: Path, two_chunk_episode):
    synthesize_conversation(CONVERSATION, _Producer(), "model", tmp_path)
    marker = started_marker(tmp_path / "partials", "conversation-1")
    synthesize_conversation(CONVERSATION, _Producer(fail_on=1), "model", tmp_path)
    assert not marker.exists()


def test_pruning_removes_only_what_is_older_than_the_bound(tmp_path: Path):
    partials = tmp_path / "partials"
    (partials / "started").mkdir(parents=True)
    old, fresh, old_mark = (
        partials / "old.json",
        partials / "fresh.json",
        partials / "started" / "c",
    )
    for path in (old, fresh, old_mark):
        path.write_text("{}")
    now = time.time()
    stale = now - MAX_AGE_SECONDS - 60
    os.utime(old, (stale, stale))
    os.utime(old_mark, (stale, stale))
    assert prune_partials(partials, now) == 2
    assert [path.name for path in partials.glob("*.json")] == ["fresh.json"]
    assert started_conversations(partials) == set()


def test_pruning_a_missing_directory_removes_nothing(tmp_path: Path):
    assert prune_partials(tmp_path / "absent") == 0

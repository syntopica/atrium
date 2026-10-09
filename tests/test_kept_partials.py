"""A map chunk's synthesis is kept on disk and its worker slot released at once.

Unacked partials held the worker queue's twenty outstanding slots while their
episodes waited to submit the next chunk, and the local lane stalled from
2026-10-08 20:01: no episode could finish, so none could ack.
"""

from pathlib import Path

import pytest

from atrium.synthesize import kept_chunk_synthesis as kept_module
from atrium.synthesize.synthesize_episode import synthesize_episode

EVENTS = [
    {"id": str(index), "role": "user", "text": f"turn {index}", "createdAt": None}
    for index in range(4)
]
EPISODE = {"event_indexes": [0, 1, 2, 3], "chunks": [[0, 1], [2, 3]]}


class _Producer:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, system_text, user_text, tool):
        self.calls += 1
        return {
            "input": {"title": f"t{self.calls}", "summary": "s"},
            "model": "m",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "worker_results": [{"job_id": f"j{self.calls}", "result_id": f"r{self.calls}"}],
        }


@pytest.fixture
def acked(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(kept_module, "ack_worker_results", seen.extend)
    return seen


def test_each_partial_is_acked_as_soon_as_it_is_kept(tmp_path: Path, acked):
    producer = _Producer()
    reduced = synthesize_episode(EPISODE, EVENTS, producer, tmp_path, "model")
    assert producer.calls == 3
    assert [result["job_id"] for result in acked] == ["j1", "j2"]
    # The reduce result is kept too, but acked by the caller after the record.
    assert reduced["worker_results"] == [{"job_id": "j3", "result_id": "r3"}]
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_a_later_pass_resumes_from_the_kept_partials(tmp_path: Path, acked):
    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    again = _Producer()
    synthesize_episode(EPISODE, EVENTS, again, tmp_path, "model")
    assert again.calls == 0


def test_a_read_acks_again_in_case_a_stop_came_between_keeping_and_acking(tmp_path: Path, acked):
    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    acked.clear()
    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    assert [result["job_id"] for result in acked] == ["j1", "j2"]


def test_an_identical_single_chunk_episode_reuses_the_kept_result(tmp_path: Path, acked):
    """The worker key is the prompt's hash; a second identical episode must not spend it."""
    single = {"event_indexes": [0, 1], "chunks": [[0, 1]]}
    synthesize_episode(single, EVENTS, _Producer(), tmp_path, "model")
    again = _Producer()
    synthesize_episode(single, EVENTS, again, tmp_path, "model")
    assert again.calls == 0


def test_an_empty_synthesis_is_not_kept(tmp_path: Path, acked):
    def empty(system_text, user_text, tool):
        return {"input": {}, "model": "m", "usage": {}, "worker_results": []}

    synthesize_episode({"event_indexes": [0], "chunks": [[0]]}, EVENTS, empty, tmp_path, "m")
    assert list(tmp_path.glob("*.json")) == []


def test_another_model_does_not_reuse_the_partials(tmp_path: Path, acked):
    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    other = _Producer()
    synthesize_episode(EPISODE, EVENTS, other, tmp_path, "other-model")
    assert other.calls == 3


def test_without_a_partials_directory_nothing_is_kept_or_acked(tmp_path: Path, acked):
    reduced = synthesize_episode(EPISODE, EVENTS, _Producer())
    assert acked == []
    assert len(reduced["worker_results"]) == 3


def test_reusing_a_partial_keeps_it_from_the_age_prune(tmp_path: Path, acked):
    """A conversation retrying its reduce for a month must not lose the chunks it reads."""
    import os

    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    for path in tmp_path.glob("*.json"):
        os.utime(path, (0, 0))
    synthesize_episode(EPISODE, EVENTS, _Producer(), tmp_path, "model")
    assert all(path.stat().st_mtime > 0 for path in tmp_path.glob("*.json"))

"""A pass does not segment again a conversation it already finished at the same content.

Every pass used to load and segment every conversation to learn that nothing
was left, at 1.2 s each, so on 65,623 conversations each 55-minute pass died
at about 7,100 having synthesized nothing (2026-11-06).
"""

import json
from typing import Any

import pytest

from atrium.cli import main
from atrium.synthesize import synthesize_conversation as synthesize_module
from atrium.synthesize.complete_marker import complete_marker
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError


def _archive(tmp_path, rows: list[tuple[str, str]]):
    archive = tmp_path / "archive.jsonl"
    lines: list[dict[str, Any]] = [{"kind": "rocket-agents-conversation-export"}]
    lines += [{"id": name, "updatedAt": stamp, "events": []} for name, stamp in rows]
    archive.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return archive


@pytest.fixture
def walked(monkeypatch, tmp_path):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path / "state"))
    seen: list[str] = []

    def fake(conversation, *args, **kwargs):
        seen.append(conversation["id"])
        if conversation["id"] == "conv-wall":
            raise QuotaExhaustedError("spent")
        return {"synthesized": 0, "skipped": 1}

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", fake)
    return seen


def _pass(archive) -> int:
    return main(["synthesize", str(archive), "--producer", "local", "--workers", "1"])


def test_a_finished_conversation_is_not_walked_again(walked, tmp_path):
    archive = _archive(tmp_path, [("conv-a", "2026-11-02"), ("conv-b", "2026-11-01")])
    assert _pass(archive) == 0
    assert walked == ["conv-a", "conv-b"]
    walked.clear()
    assert _pass(archive) == 0
    assert walked == []


def test_new_content_is_walked_again(walked, tmp_path):
    assert _pass(_archive(tmp_path, [("conv-a", "2026-11-01")])) == 0
    walked.clear()
    assert _pass(_archive(tmp_path, [("conv-a", "2026-11-03")])) == 0
    assert walked == ["conv-a"]


def test_work_left_at_a_wall_is_not_marked(walked, tmp_path):
    registry = tmp_path / "state" / "synthesis"
    assert _pass(_archive(tmp_path, [("conv-wall", "2026-11-01")])) == 0
    marker = complete_marker(registry, {"id": "conv-wall", "updatedAt": "2026-11-01"})
    assert marker is not None
    assert not marker.exists()


def test_a_conversation_without_a_timestamp_is_never_marked(tmp_path):
    assert complete_marker(tmp_path, {"id": "conv-a"}) is None

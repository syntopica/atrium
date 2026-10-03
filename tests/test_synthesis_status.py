"""A finished synthesis pass publishes its tallies; a dry run publishes nothing."""

import json

from atrium.cli import main
from atrium.synthesize import synthesize_conversation as synthesize_module
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError

SENTINEL = "a conversation body that must never be published"


def _archive(tmp_path):
    archive = tmp_path / "archive.jsonl"
    lines = [{"kind": "rocket-agents-conversation-export", "schemaVersion": 2}]
    lines += [
        {
            "id": conversation,
            "updatedAt": updated,
            "events": [{"id": "e1", "text": SENTINEL}],
        }
        for conversation, updated in (("conv-new", "2026-09-02"), ("conv-old", "2026-09-01"))
    ]
    archive.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return archive


def _synthesize(tmp_path, *extra):
    return main(["synthesize", str(_archive(tmp_path)), "--workers", "1", *extra])


def test_a_pass_publishes_counts_and_instants(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))

    def fake(conversation, *args, **kwargs):
        if conversation["id"] == "conv-old":
            raise QuotaExhaustedError("spent")
        return {"synthesized": 2, "skipped": 1}

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", fake)
    assert _synthesize(tmp_path) == 0
    published = state / "status" / "synthesis.json"
    text = published.read_text()
    assert SENTINEL not in text
    assert str(tmp_path) not in text
    document = json.loads(text)
    assert document["schemaVersion"] == 1
    last = document["lastPass"]
    assert {key: last[key] for key in ("conversations", "synthesized", "skipped", "failed")} == {
        "conversations": 2,
        "synthesized": 2,
        "skipped": 1,
        "failed": 0,
    }
    assert last["deferred"] == 1
    assert last["producer"] == "agy"
    assert last["startedAt"] <= last["finishedAt"] <= document["writtenAt"]
    assert document["writtenAt"].endswith("Z")
    assert [path.name for path in published.parent.iterdir()] == ["synthesis.json"]


def test_a_failing_pass_still_reports_itself(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))

    def broken(*args, **kwargs):
        raise RuntimeError("producer exploded")

    monkeypatch.setattr(synthesize_module, "synthesize_conversation", broken)
    assert _synthesize(tmp_path) == 1
    document = json.loads((state / "status" / "synthesis.json").read_text())
    assert document["lastPass"]["failed"] == 2
    assert "exploded" not in json.dumps(document)


def test_a_dry_run_publishes_nothing(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    assert _synthesize(tmp_path, "--dry-run") == 0
    assert not (state / "status").exists()

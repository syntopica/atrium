"""A stamp that says which rule the ids follow can be wrong; the archive cannot."""

import json

from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.job_identity import job_identity
from atrium.synthesize.qualify_event_id import qualify_event_id
from atrium.synthesize.repair_mis_stamped_records import repair_mis_stamped_records
from atrium.synthesize.synthesis_registry import write_record

CONVERSATION = "c" * 64


def _archive(path, event_ids):
    manifest = {"kind": "rocket-agents-conversation-export", "schemaVersion": 2, "records": 1}
    record = {
        "schemaVersion": 2,
        "id": CONVERSATION,
        "events": [{"id": event_id} for event_id in event_ids],
    }
    path.write_text(json.dumps(manifest) + "\n" + json.dumps(record) + "\n")
    return path


def _record(event_ids, stamp):
    episode = episode_identity(CONVERSATION, event_ids)
    return {
        "job_key": job_identity(CONVERSATION, "rev-1", episode, "codex-cli-default"),
        "conversation_id": CONVERSATION,
        "revision_sha256": "rev-1",
        "episode_id": episode,
        "event_ids": event_ids,
        "model_requested": "codex-cli-default",
        "event_id_schema": stamp,
        "output": {"facts": ["paid for once"]},
    }


def test_a_record_stamped_current_with_legacy_ids_is_repaired(tmp_path):
    # Exactly what happened live: a synthesis pass ran with the stamping code
    # against a not-yet-upgraded archive, so 201 records claimed schema 2 while
    # carrying schema 1 ids, and the stamp-based re-key skipped them.
    legacy_ids = ["e1", "e2"]
    upgraded = [qualify_event_id(CONVERSATION, event_id) for event_id in legacy_ids]
    archive = _archive(tmp_path / "archive.jsonl", upgraded)
    registry = tmp_path / "registry"
    mis_stamped = _record(legacy_ids, stamp=2)
    write_record(registry, mis_stamped["job_key"], mis_stamped)

    planned = repair_mis_stamped_records(registry, archive)
    assert planned["repaired"] == 1
    assert planned["backup"] is None, "a plan must not copy or write anything"

    applied = repair_mis_stamped_records(registry, archive, apply=True)
    assert applied["repaired"] == 1
    assert applied["backup"] is not None

    remaining = list((registry / "records").glob("*.json"))
    assert len(remaining) == 1
    repaired = json.loads(remaining[0].read_text())
    assert repaired["event_ids"] == upgraded
    assert repaired["output"] == mis_stamped["output"]
    assert repair_mis_stamped_records(registry, archive)["repaired"] == 0


def test_a_record_that_agrees_with_the_archive_is_left_alone(tmp_path):
    upgraded = [qualify_event_id(CONVERSATION, "e1")]
    archive = _archive(tmp_path / "archive.jsonl", upgraded)
    registry = tmp_path / "registry"
    healthy = _record(upgraded, stamp=2)
    write_record(registry, healthy["job_key"], healthy)

    report = repair_mis_stamped_records(registry, archive, apply=True)
    assert report == {"repaired": 0, "intact": 1, "unexplained": 0, "applied": True, "backup": None}


def test_ids_absent_under_either_rule_are_reported_not_guessed_at(tmp_path):
    archive = _archive(tmp_path / "archive.jsonl", ["something-else"])
    registry = tmp_path / "registry"
    stranded = _record(["e1"], stamp=2)
    write_record(registry, stranded["job_key"], stranded)

    report = repair_mis_stamped_records(registry, archive, apply=True)

    assert report["unexplained"] == 1
    assert report["repaired"] == 0
    # Guessing at a different fault would destroy the evidence for it.
    assert (
        json.loads((registry / "records" / f"{stranded['job_key']}.json").read_text()) == stranded
    )

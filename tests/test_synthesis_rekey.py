"""The registry re-key must land exactly where a fresh synthesis would."""

import hashlib
import json

from atrium.synthesize.episode_identity import episode_identity
from atrium.synthesize.event_id_schema import EVENT_ID_SCHEMA
from atrium.synthesize.job_identity import job_identity
from atrium.synthesize.qualify_event_id import qualify_event_id
from atrium.synthesize.rekey_synthesis_record import rekey_synthesis_record
from atrium.synthesize.rekey_synthesis_registry import rekey_synthesis_registry
from atrium.synthesize.synthesis_registry import record_path, write_record

CONVERSATION = "c" * 64


def _legacy_record(event_ids: list[str], model: str = "codex-cli-default") -> dict:
    episode = episode_identity(CONVERSATION, event_ids)
    return {
        "job_key": job_identity(CONVERSATION, "rev-1", episode, model),
        "conversation_id": CONVERSATION,
        "revision_sha256": "rev-1",
        "episode_id": episode,
        "event_ids": event_ids,
        "model_requested": model,
        "output": {"facts": ["already paid for"]},
        "output_sha256": hashlib.sha256(b"x").hexdigest(),
    }


def test_rekey_matches_the_identity_a_fresh_synthesis_would_derive():
    # The whole migration rests on this: the new ids are a pure function of the
    # old ones, so an episode that was already synthesized must come out with
    # the identity the synthesizer would give it after the archive upgrade. If
    # it does not, `synthesize` pays the model again for output already held.
    legacy = _legacy_record(["e1", "e2"])
    rekeyed = rekey_synthesis_record(legacy)

    upgraded_event_ids = [
        qualify_event_id(CONVERSATION, "e1"),
        qualify_event_id(CONVERSATION, "e2"),
    ]
    expected_episode = episode_identity(CONVERSATION, upgraded_event_ids)

    assert rekeyed["event_ids"] == upgraded_event_ids
    assert rekeyed["episode_id"] == expected_episode
    assert rekeyed["job_key"] == job_identity(
        CONVERSATION, "rev-1", expected_episode, "codex-cli-default"
    )
    assert rekeyed["event_id_schema"] == EVENT_ID_SCHEMA


def test_rekey_carries_the_paid_output_through_untouched():
    legacy = _legacy_record(["e1"])
    rekeyed = rekey_synthesis_record(legacy)
    assert rekeyed["output"] == legacy["output"]
    assert rekeyed["output_sha256"] == legacy["output_sha256"]
    assert rekeyed["revision_sha256"] == legacy["revision_sha256"]


def test_rekey_is_idempotent():
    once = rekey_synthesis_record(_legacy_record(["e1", "e2"]))
    assert rekey_synthesis_record(once) == once


def test_registry_pass_moves_the_file_and_leaves_no_second_generation(tmp_path):
    legacy = _legacy_record(["e1", "e2"])
    write_record(tmp_path, legacy["job_key"], legacy)

    planned = rekey_synthesis_registry(tmp_path)
    assert planned == {"moved": 1, "already": 0, "collided": 0, "collisions": [], "applied": False}
    assert record_path(tmp_path, legacy["job_key"]).exists(), "a plan must not touch the registry"

    applied = rekey_synthesis_registry(tmp_path, apply=True)
    assert applied["moved"] == 1

    # Both generations surviving is the failure this migration exists to
    # prevent: ingest-synthesis keys on episode_id, so two files would index
    # the same episode twice.
    remaining = sorted(path.name for path in (tmp_path / "records").glob("*.json"))
    expected = rekey_synthesis_record(legacy)["job_key"]
    assert remaining == [f"{expected}.json"]
    assert (
        json.loads((tmp_path / "records" / f"{expected}.json").read_text())["output"]
        == legacy["output"]
    )

    # A second pass has nothing left to do.
    assert rekey_synthesis_registry(tmp_path, apply=True)["moved"] == 0


def test_registry_pass_reports_a_divergent_collision_instead_of_overwriting(tmp_path):
    legacy = _legacy_record(["e1"])
    write_record(tmp_path, legacy["job_key"], legacy)
    occupied = rekey_synthesis_record(legacy)
    write_record(tmp_path, occupied["job_key"], {**occupied, "output": {"facts": ["different"]}})

    report = rekey_synthesis_registry(tmp_path, apply=True)

    assert report["collided"] == 1
    assert report["moved"] == 0
    assert json.loads(record_path(tmp_path, legacy["job_key"]).read_text()) == legacy


def test_qualified_id_matches_the_rocket_agents_implementation():
    """Byte-for-byte against `qualifyConversationEventIds.ts`, run 2026-08-31.

    Two implementations of one identity is exactly how a migration silently
    orphans everything it touches, so the reference values come from running
    the TypeScript, not from reading it.
    """
    assert qualify_event_id("c" * 64, "e1") == (
        "3d9c6568fadc881c22294c7f7ece9fbfdc5fd05f2b88e9c58ba0c7f849ef4b87"
    )
    assert qualify_event_id("c" * 64, "0" * 64) == (
        "38372940b32004f4b41fe623dd47998c34b93322338039e30e699aea6264c064"
    )

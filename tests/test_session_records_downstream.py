"""A session record is served, indexed for its project, backfill-skipped, and re-key safe."""

import json

from atrium.cli import main
from atrium.recall.recent_episodes import recent_episodes
from atrium.session.session_covered_conversations import session_covered_conversations
from atrium.store.open_store import open_store
from atrium.synthesize.rekey_synthesis_record import rekey_synthesis_record
from atrium.synthesize.synthesis_registry import write_record

RECORD = {
    "job_key": "k" * 32,
    "conversation_id": "c" * 64,
    "episode_id": "e" * 24,
    "event_ids": [],
    "event_id_schema": 1,
    "segmentation": "session-self-v1",
    "model_requested": "session-claude",
    "authored_at": "2026-09-16T11:05:00.000Z",
    "workspace": "[HOME]/p/proj",
    "output": {"title": "Cache expiry", "summary": "TTL on read", "facts": [], "open_ends": []},
}


def test_ingest_reaches_project_recall_before_the_conversation_is_archived(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    write_record(state / "synthesis", RECORD["job_key"], RECORD)
    (state / "synthesis" / "active-recipe.json").write_text(json.dumps({"model_priority": []}))
    assert main(["ingest-synthesis"]) == 0
    connection = open_store(state / "index.sqlite3")
    try:
        hits = recent_episodes(connection, "[HOME]/p/proj", 5)
    finally:
        connection.close()
    assert [hit.text.split("\n")[0] for hit in hits] == ["Cache expiry"]


def test_session_records_name_the_conversations_the_batch_lanes_skip():
    batch = {**RECORD, "segmentation": "episode-texttiling-v1", "conversation_id": "b" * 64}
    assert session_covered_conversations([RECORD, batch]) == {"c" * 64}


def test_rekey_leaves_a_session_record_unchanged():
    assert rekey_synthesis_record(dict(RECORD)) == RECORD

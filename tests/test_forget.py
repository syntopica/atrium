"""Forgetting: records describing a retired thing as current leave the index, reversibly."""

import fcntl
import hashlib
import json
import time

import pytest
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.context.read_retirements import read_retirements
from atrium.context.retrieve_context import retrieve_context
from atrium.forget.append_ledger import append_ledger
from atrium.forget.latest_events import latest_events
from atrium.forget.restore_events import restore_events
from atrium.forget.retired_candidates import retired_candidates
from atrium.ingest.record_identity import record_identity
from atrium.ingest.to_note_records import to_note_records
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

_RETIRED = """---
title: Retired tools
type: business
---

# Retired tools

## Holded

```yaml
retired:
  since: 2026-09-22
  replaced_by: InteliFactu
  terms: [Holded]
```

## MemPalace

```yaml
retired:
  since: 2026-08-30
  replaced_by: Atrium
  terms: [MemPalace]
```
"""


def _conversation(conversation_id, text, timestamp, role="assistant"):
    return {
        "id": conversation_id,
        "source": "test",
        "provenance": {"contentSha256": f"sha-{conversation_id}"},
        "events": [
            {"id": "e1", "kind": "message", "role": role, "text": text, "timestamp": timestamp}
        ],
    }


def _archive(path, conversations):
    lines = [json.dumps({"kind": "rocket-agents-conversation-export"})]
    path.write_text("\n".join(lines + [json.dumps(c) for c in conversations]))


def _history(index):
    connection = open_store(index, read_only=True)
    rows = connection.execute(load_test_sql("forget/history_records")).fetchall()
    connection.close()
    return {row[0] for row in rows}


def _write_note(index, path="brain/retired.md", text=_RETIRED):
    connection = open_store(index)
    with connection:
        write_conversation(
            connection,
            path,
            to_note_records(
                {"path": path, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}
            ),
        )
    connection.close()


@pytest.fixture
def instance(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("ATRIUM_STATE", str(state))
    archive = tmp_path / "archive.jsonl"
    _archive(
        archive,
        [
            _conversation(
                "old", "Facturas emitidas en Holded para Vibra Lab", "2026-09-10T10:00:00Z"
            ),
            _conversation(
                "new", "Holded ya no se usa, todo en InteliFactu", "2026-10-01T10:00:00Z"
            ),
            _conversation("other", "Remesa SEPA enviada al banco", "2026-09-01T10:00:00Z"),
            _conversation("palace", "mempalace_search devolvio vacio", "2026-08-01T10:00:00Z"),
            _conversation("word", "Unholded stock count", "2026-09-01T10:00:00Z"),
        ],
    )
    index = state / "index.sqlite3"
    main(["--index", str(index), "ingest", str(archive)])
    _write_note(index)
    return state, index, archive


def _ids(*names):
    return {record_identity(name, "e1") for name in names}


def test_one_note_declares_several_retirements(instance):
    _, index, _ = instance
    connection = open_store(index, read_only=True)
    found = read_retirements(connection)
    connection.close()
    assert sorted((one.terms, one.since) for one in found) == [
        (("Holded",), "2026-09-22"),
        (("MemPalace",), "2026-08-30"),
    ]


def test_only_history_from_before_the_date_naming_a_term_is_a_candidate(instance):
    _, index, _ = instance
    connection = open_store(index, read_only=True)
    found = retired_candidates(connection, read_retirements(connection))
    connection.close()
    # "palace" names mempalace_search: `_` is a word character, so not a whole-word
    # mention of MemPalace; "new" postdates the retirement; notes never qualify.
    assert set(found) == _ids("old")


def test_forget_reports_first_then_applies_and_the_next_ingest_drops_the_record(instance, capsys):
    state, index, archive = instance
    main(["--index", str(index), "forget"])
    report = json.loads(capsys.readouterr().out.splitlines()[0])
    assert (report["new"], report["applied"]) == (1, False)
    assert not (state / "forget" / "ledger.jsonl").exists()

    main(["--index", str(index), "forget", "--apply"])
    assert json.loads(capsys.readouterr().out.splitlines()[0])["applied"] is True
    assert _ids("old") <= _history(index)  # nothing leaves until the next ingest
    main(["--index", str(index), "ingest", str(archive)])
    assert _history(index) == _ids("new", "other", "palace", "word")


def test_a_rebuilt_index_still_leaves_the_record_out(instance, tmp_path):
    _, index, archive = instance
    main(["--index", str(index), "forget", "--apply"])
    rebuilt = tmp_path / "rebuilt.sqlite3"
    main(["--index", str(rebuilt), "ingest", str(archive)])
    assert _ids("old").isdisjoint(_history(rebuilt))


def test_a_restore_brings_the_record_back_and_survives_the_next_pass(instance, capsys):
    _, index, archive = instance
    main(["--index", str(index), "forget", "--apply"])
    main(["--index", str(index), "ingest", str(archive)])
    main(["--index", str(index), "forget", "--restore", "retired:Holded", "--apply"])
    main(["--index", str(index), "forget", "--apply"])
    capsys.readouterr()
    main(["--index", str(index), "ingest", str(archive)])
    assert _ids("old") <= _history(index)
    main(["--index", str(index), "forget"])
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["kept_by_restore"] == 1


def test_forget_refuses_while_a_refresh_holds_the_instance(instance, capsys):
    state, index, _ = instance
    with (state / "refresh.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert main(["--index", str(index), "forget", "--apply"]) == 3
    assert "refused" in capsys.readouterr().out
    assert not (state / "forget" / "ledger.jsonl").exists()


def test_a_cut_final_line_is_skipped_dropped_by_the_next_append_and_a_damaged_one_raises(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_ledger(ledger, [{"event": "forget", "record_id": "a", "rule": "retired"}])
    with ledger.open("a") as handle:
        handle.write('{"event": "forget", "record_id": "b"')
    assert set(latest_events(ledger)) == {"a"}
    append_ledger(ledger, [{"event": "restore", "record_id": "a"}])
    assert latest_events(ledger)["a"]["event"] == "restore"
    assert "b" not in latest_events(ledger)
    ledger.write_text('not json\n{"event": "forget", "record_id": "a"}\n')
    with pytest.raises(ValueError, match="not valid JSON"):
        latest_events(ledger)


def test_restore_selects_by_id_rule_or_detail():
    latest = {
        "a": {"event": "forget", "rule": "retired", "detail": "Holded"},
        "b": {"event": "forget", "rule": "retired", "detail": "MemPalace"},
        "c": {"event": "restore"},
    }
    assert [e["record_id"] for e in restore_events("retired:Holded", latest, "d")] == ["a"]
    assert [e["record_id"] for e in restore_events("retired", latest, "d")] == ["a", "b"]
    assert [e["record_id"] for e in restore_events("b", latest, "d")] == ["b"]


def test_a_question_naming_the_term_learns_what_was_forgotten(instance):
    state, index, archive = instance
    main(["--index", str(index), "forget", "--apply"])
    main(["--index", str(index), "ingest", str(archive)])
    (state / "last-refresh").write_text(str(time.time()))
    project = state.parent / "books"
    (project / ".git").mkdir(parents=True)
    connection = open_store(index)
    asked = retrieve_context(
        connection, "facturas holded vibra lab", project=None, lane="words", state=state
    )
    plain = retrieve_context(
        connection, "remesa sepa banco", project=None, lane="words", state=state
    )
    connection.close()
    (holded,) = [one for one in asked["retired"] if one["terms"] == ["Holded"]]
    assert holded["forgotten"] == 1
    assert holded["restore"] == "atrium forget --restore retired:Holded --apply"
    assert all("forgotten" not in one for one in plain["retired"])


def test_echo_rule_selects_a_lone_echo_episode_and_spares_a_real_one(tmp_path):
    from atrium.forget.echo_forget_plan import echo_forget_plan

    registry = tmp_path / "synthesis"
    (registry / "records").mkdir(parents=True)
    for episode, event in (("echo", "e1"), ("real", "e2"), ("pair", "e1")):
        event_ids = [event] if episode != "pair" else ["e1", "e2"]
        (registry / "records" / f"{episode}.json").write_text(
            json.dumps({"episode_id": episode, "conversation_id": "c", "event_ids": event_ids})
        )
    archive = tmp_path / "archive.jsonl"
    conversation = _conversation("c", "Structured output provided successfully", "2026-10-01")
    conversation["events"].append({"id": "e2", "kind": "message", "role": "user", "text": "ok?"})
    _archive(archive, [conversation])
    ledger = tmp_path / "forget.jsonl"

    events, report = echo_forget_plan(registry, archive, ledger, "2026-10-16")

    assert [event["record_id"] for event in events] == [record_identity("synthesis/c", "echo")]
    assert events[0]["rule"] == "harness-echo"
    assert report["new_by_echo"] == {"Structured output provided successfully": 1}
    append_ledger(ledger, events)
    assert echo_forget_plan(registry, archive, ledger, "2026-10-17")[0] == []
    assert len(restore_events("harness-echo", latest_events(ledger), "2026-10-17")) == 1

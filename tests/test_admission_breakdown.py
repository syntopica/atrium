"""Ingest reports what it admitted and what each rule turned away.

A bare row count is exactly the number that looked healthy while 162,225
tool-call, tool-result and thinking records were being filed as conversation
during the mempalace recovery.
"""

import json

from atrium.cli import main
from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.to_records import to_records

LONG = "x" * 200


def _conversation(events):
    return {
        "id": "conv-1",
        "source": "pi",
        "startedAt": "2026-08-01T00:00:00Z",
        "provenance": {"contentSha256": "abc123"},
        "events": events,
    }


def _message(role, text, event_id="e1"):
    return {"id": event_id, "kind": "message", "role": role, "text": text}


def test_every_rejection_rule_is_counted_under_its_own_name():
    conversation = _conversation(
        [
            _message("user", LONG, "keep"),
            _message("assistant", LONG, "keep2"),
            {"id": "t", "kind": "tool_result", "role": "user", "text": LONG},
            {"id": "th", "kind": "thinking", "role": "assistant", "text": LONG},
            {"id": "s", "kind": "message", "role": "system", "text": LONG},
            _message("user", "ok", "ack"),
            {"kind": "message", "role": "user", "text": LONG},
        ]
    )
    tally = AdmissionTally()
    records = list(to_records(conversation, tally))
    assert len(records) == 2
    assert tally.admitted == {"user": 1, "assistant": 1}
    assert tally.rejected == {
        "kind tool_result": 1,
        "kind thinking": 1,
        "role system": 1,
        "empty or acknowledgement": 1,
        "missing event id": 1,
    }


def test_without_a_tally_admission_still_behaves_identically():
    conversation = _conversation([_message("user", LONG), _message("user", "ok", "a")])
    assert len(list(to_records(conversation))) == 1


def test_notes_ingest_prints_the_breakdown_too(tmp_path, capsys):
    root = tmp_path / "notes"
    (root / ".obsidian").mkdir(parents=True)
    (root / "keep.md").write_text("# Keep\n\na body worth keeping")
    (root / ".obsidian" / "hidden.md").write_text("# Hidden\n\nnever read")
    (root / "drafts").mkdir()
    (root / "drafts" / "draft.md").write_text("# Draft\n\nexcluded by name")
    index = tmp_path / "index.sqlite3"
    code = main(["--index", str(index), "ingest-notes", str(root), "--exclude", "drafts"])
    out = capsys.readouterr().out
    assert code == 0
    assert "admitted: 1 note" in out
    assert "1 hidden directory files" in out
    assert "1 excluded drafts files" in out


def test_ingest_prints_the_breakdown(tmp_path, capsys):
    archive = tmp_path / "archive.jsonl"
    archive.write_text(
        json.dumps({"kind": "rocket-agents-conversation-export", "records": 1})
        + "\n"
        + json.dumps(
            _conversation(
                [
                    _message("user", LONG, "keep"),
                    {"id": "t", "kind": "tool_result", "role": "user", "text": LONG},
                ]
            )
        )
        + "\n",
        encoding="utf-8",
    )
    index = tmp_path / "index.sqlite3"
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    out = capsys.readouterr().out
    assert "admitted: 1 user" in out
    assert "rejected: 1 kind tool_result" in out

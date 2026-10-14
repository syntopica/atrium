"""Retired tools declared on a note: outdated history sinks, and the answer says so."""

import hashlib
import time

from atrium.context.demote_retired import demote_retired
from atrium.context.parse_retirement import parse_retirement
from atrium.context.retired_mentions import retired_mentions
from atrium.context.retirement import Retirement
from atrium.context.retrieve_context import retrieve_context
from atrium.ingest.to_note_records import to_note_records
from atrium.record import Record
from atrium.retrieve.hit import Hit
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

_NOTE = """---
title: Holded
type: business
retired:
  since: 2026-09-22
  replaced_by: InteliFactu
  terms: [Holded, 'Holded API']
sources:
  - somewhere
---

# Holded

Holded is retired; invoicing moved to InteliFactu.
"""

_HOLDED = Retirement(("Holded",), "2026-09-22", "InteliFactu", "brain/business/holded.md")


def _hit(record_id, text, authored_at, role="assistant", conversation_id="c"):
    return Hit(record_id, text, 1.0, "words", conversation_id, "a" * 64, authored_at, "p", role)


def test_the_block_is_read_from_frontmatter():
    assert parse_retirement(_NOTE, "brain/business/holded.md") == Retirement(
        ("Holded", "Holded API"), "2026-09-22", "InteliFactu", "brain/business/holded.md"
    )


def test_an_incomplete_block_declares_nothing():
    assert parse_retirement("retired:\n  replaced_by: X\n  terms: [Y]\n", "n.md") is None
    assert parse_retirement("retired:\n  since: soon\n  terms: [Y]\n", "n.md") is None
    assert parse_retirement("# Retired: nothing here\n", "n.md") is None


def test_history_before_the_date_sinks_and_later_history_stays():
    candidates = [
        (_hit("old", "Facturas emitidas en Holded", "2026-09-10T10:00:00Z"), "history", None),
        (_hit("new", "Holded ya no se usa, todo en InteliFactu", "2026-10-01"), "history", None),
        (_hit("other", "Remesa SEPA enviada", "2026-09-01"), "history", None),
    ]
    mentions = retired_mentions(candidates, [_HOLDED])
    order = [hit.record_id for hit, _, _ in demote_retired(candidates, mentions, "facturas")]
    assert order == ["new", "other", "old"]


def test_a_question_naming_the_retired_thing_keeps_its_history_in_place():
    candidates = [
        (_hit("old", "Facturas emitidas en Holded", "2026-09-10"), "history", None),
        (_hit("other", "Remesa SEPA enviada", "2026-09-01"), "history", None),
    ]
    mentions = retired_mentions(candidates, [_HOLDED])
    order = [hit.record_id for hit, _, _ in demote_retired(candidates, mentions, "holded archive")]
    assert order == ["old", "other"]


def test_only_the_declaring_note_sinks_among_curated_notes():
    candidates = [
        (_hit("own", "Holded templates", None, "note", _HOLDED.note), "curated", None),
        (_hit("else", "Holded was retired", None, "note", "brain/x.md"), "curated", None),
        (_hit("plain", "Quarter close", None, "note", "brain/y.md"), "curated", None),
    ]
    mentions = retired_mentions(candidates, [_HOLDED])
    order = [hit.record_id for hit, _, _ in demote_retired(candidates, mentions, "invoices")]
    assert order == ["else", "plain", "own"]


def test_a_word_inside_another_word_is_not_a_mention():
    candidates = [(_hit("x", "Unholded stock", "2026-01-01"), "history", None)]
    assert retired_mentions(candidates, [_HOLDED]) == {}


def test_context_names_the_retirement_and_marks_its_evidence(tmp_path):
    project = tmp_path / "books"
    (project / ".git").mkdir(parents=True)
    state = tmp_path / "state"
    state.mkdir()
    (state / "last-refresh").write_text(str(time.time()))
    connection = open_store(state / "index.sqlite3")
    with connection:
        for name, text, when in [
            (
                "old",
                "Monthly invoices for hosting: monthly hosting invoices in Holded",
                "2026-09-10T00:00:00Z",
            ),
            ("new", "Monthly invoices issued in InteliFactu for hosting", "2026-10-10T00:00:00Z"),
        ]:
            record = Record(
                name, name, name, "a" * 64, "fixture", "assistant", text, when,
                str(project), None, 0,
            )  # fmt: skip
            write_conversation(connection, name, [record])
        path = "brain/business/holded.md"
        write_conversation(
            connection,
            path,
            to_note_records(
                {"path": path, "text": _NOTE, "sha256": hashlib.sha256(_NOTE.encode()).hexdigest()}
            ),
        )
    result = retrieve_context(
        connection, "monthly invoices hosting", project=project, lane="words", state=state
    )
    history = [item["record_id"] for item in result["evidence"] if item["role"] == "assistant"]
    assert history == ["new", "old"]
    assert [item.get("retired") for item in result["evidence"] if item["record_id"] == "old"] == [
        "Holded"
    ]
    asked = retrieve_context(
        connection, "monthly invoices hosting holded", project=project, lane="words", state=state
    )
    assert [item["record_id"] for item in asked["evidence"] if item["role"] == "assistant"] == [
        "old",
        "new",
    ]
    assert result["retired"] == [
        {
            "terms": ["Holded", "Holded API"],
            "since": "2026-09-22",
            "replaced_by": "InteliFactu",
            "note": path,
        }
    ]

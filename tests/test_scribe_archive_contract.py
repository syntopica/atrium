"""Ingest reads the export scribe actually writes, not a hand-built imitation.

``fixtures/scribe_archive_contract_v2.jsonl`` is a verbatim copy of scribe's
``fixtures/archive-contract/v2/export.jsonl`` (scribe ``199f393``), which scribe's
own test pins to its code. Replace it, never edit it, when scribe changes the
format.
"""

from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.ingest.to_records import to_records
from atrium.synthesize.turn_blocks import turn_blocks

CONTRACT = Path(__file__).parent / "fixtures" / "scribe_archive_contract_v2.jsonl"


def _admitted():
    return {
        conversation["source"]: [(r.role, r.text) for r in to_records(conversation)]
        for conversation in read_archive(CONTRACT)
    }


def test_the_manifest_is_skipped_and_both_providers_are_read():
    assert sorted(c["source"] for c in read_archive(CONTRACT)) == ["claude-code", "codex"]


def test_codex_tool_calls_and_their_output_are_not_records():
    assert _admitted()["codex"] == [
        ("user", "Run the tests"),
        ("assistant", "All 42 tests pass."),
    ]


def test_claude_code_tool_output_is_archived_as_tool_and_not_admitted():
    """Scribe ``199f393`` archives a line of only ``tool_result`` blocks as role
    ``tool``, so the tool output no longer reaches the records as user text."""
    assert _admitted()["claude-code"] == [
        ("user", "Why does the deploy fail?"),
        ("assistant", "Reading the deploy script.\ntool: Read"),
        ("assistant", "Line 2 exits with status 3."),
    ]


def test_claude_code_tool_output_stays_inside_the_turn_that_caused_it():
    claude = next(c for c in read_archive(CONTRACT) if c["source"] == "claude-code")
    messages = [i for i, e in enumerate(claude["events"]) if e.get("kind") == "message"]
    blocks = turn_blocks(claude["events"])
    assert [b["human_text"] for b in blocks] == ["Why does the deploy fail?"]
    assert blocks[0]["event_indexes"] == messages

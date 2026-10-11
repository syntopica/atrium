"""Ingest reads the export scribe actually writes, not a hand-built imitation.

``fixtures/scribe_archive_contract_v2.jsonl`` is a verbatim copy of scribe's
``fixtures/archive-contract/v2/export.jsonl`` (scribe ``2d9a1af``), which scribe's
own test pins to its code. Replace it, never edit it, when scribe changes the
format.
"""

from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.ingest.to_records import to_records

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


def test_claude_code_tool_output_is_still_admitted_as_a_user_message():
    """Known archive bug, pinned here so its fix is visible: scribe files a
    ``tool_result`` line as ``kind: message, role: user`` (scribe TODO, "Event
    classification"). When the v2 fixture lands, the second user record goes."""
    assert _admitted()["claude-code"] == [
        ("user", "Why does the deploy fail?"),
        ("assistant", "Reading the deploy script.\ntool: Read"),
        ("user", "1\tset -e\n2\texit 3"),
        ("assistant", "Line 2 exits with status 3."),
    ]

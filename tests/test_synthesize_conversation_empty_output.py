from pathlib import Path

import pytest

from atrium.synthesize.empty_synthesis_error import EmptySynthesisError
from atrium.synthesize.synthesize_conversation import synthesize_conversation


def _conversation() -> dict:
    return {
        "id": "c" * 64,
        "source": "claude-code",
        "schemaVersion": 2,
        "provenance": {"contentSha256": "a" * 64},
        "startedAt": "2026-09-04T10:00:00Z",
        "events": [
            {"id": "e1", "kind": "message", "role": "user", "text": "how does the cache expire"},
            {"id": "e2", "kind": "message", "role": "assistant", "text": "by TTL, checked on read"},
        ],
    }


def test_empty_output_writes_no_record(tmp_path: Path) -> None:
    def empty_producer(_system: str, _user: str, _tool: dict) -> dict:
        return {
            "input": {"title": "", "summary": "", "facts": [], "open_ends": []},
            "model": "fake",
            "usage": {},
        }

    with pytest.raises(EmptySynthesisError):
        synthesize_conversation(_conversation(), empty_producer, "fake", tmp_path)
    assert (
        not list((tmp_path / "records").glob("*.json")) if (tmp_path / "records").exists() else True
    )


def test_real_output_is_written(tmp_path: Path) -> None:
    def producer(_system: str, _user: str, _tool: dict) -> dict:
        return {
            "input": {
                "title": "Cache TTL",
                "summary": "Expiry is by TTL.",
                "facts": [],
                "open_ends": [],
            },
            "model": "fake",
            "usage": {},
        }

    counts = synthesize_conversation(_conversation(), producer, "fake", tmp_path)
    assert counts["synthesized"] == 1
    assert len(list((tmp_path / "records").glob("*.json"))) == 1

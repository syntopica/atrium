"""A synthesis record reaches the index through the same redaction as a note."""

from atrium.ingest.to_synthesis_records import to_synthesis_records

_SENTINEL = "Zq7+v>Sentinel^;x91"


def _record(**output: object) -> dict[str, object]:
    return {
        "conversation_id": "c1",
        "episode_id": "e1",
        "job_key": "k1",
        "output": {"title": "Database access", "summary": "Set up the database.", **output},
    }


def test_a_credential_in_the_facts_is_redacted() -> None:
    record = _record(facts=[f"| MySQL password | `{_SENTINEL}` |", "password: hunter2hunter2"])
    (row,) = to_synthesis_records(record, None)
    assert _SENTINEL not in row.text
    assert "hunter2hunter2" not in row.text
    assert "Set up the database." in row.text


def test_a_credential_in_the_title_is_redacted() -> None:
    (row,) = to_synthesis_records(_record(title=f"password: {_SENTINEL}x"), None)
    assert row.title is not None
    assert _SENTINEL not in row.title
    assert _SENTINEL not in row.text

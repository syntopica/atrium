"""Registry records are immutable, resumable and index-ready."""

from atrium.ingest.to_synthesis_records import to_synthesis_records
from atrium.synthesize.synthesis_registry import has_record, read_records, write_record


def _record(job_key="k1", conversation="conv-1"):
    return {
        "job_key": job_key,
        "conversation_id": conversation,
        "episode_id": "ep-abc",
        "authored_at": "2026-08-27T10:00:00Z",
        "output": {
            "title": "WAL revert",
            "summary": "The WAL switch was reverted after SIGBUS crashes.",
            "facts": ["13 SIGBUS crashes between 08:22 and 09:42"],
            "open_ends": [],
        },
    }


def test_a_record_is_written_once_and_never_overwritten(tmp_path):
    first = _record()
    write_record(tmp_path, "k1", first)
    tampered = dict(first, output=dict(first["output"], title="rewritten"))
    write_record(tmp_path, "k1", tampered)
    stored = list(read_records(tmp_path))
    assert len(stored) == 1
    assert stored[0]["output"]["title"] == "WAL revert"
    assert has_record(tmp_path, "k1")
    assert not has_record(tmp_path, "other")


def test_synthesis_records_are_namespaced_away_from_raw_conversations():
    rows = list(to_synthesis_records(_record()))
    assert len(rows) == 1
    assert rows[0].conversation_id == "synthesis/conv-1"
    assert rows[0].provider == "synthesis"
    assert rows[0].role == "synthesis"
    assert rows[0].source_sha256 == "k1"
    assert "SIGBUS" in rows[0].text


def test_an_empty_output_yields_no_index_record():
    empty = _record()
    empty["output"] = {"title": "", "summary": "", "facts": [], "open_ends": []}
    assert list(to_synthesis_records(empty)) == []

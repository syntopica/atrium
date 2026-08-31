"""The doctor must fail when the memory would answer from a world that moved on."""

import json
import sqlite3

from atrium.doctor.archive_freshness import archive_freshness
from atrium.doctor.archive_schema_coherence import archive_schema_coherence
from atrium.doctor.index_coverage import index_coverage
from atrium.doctor.read_archive_ids import read_archive_ids
from atrium.doctor.refresh_health import refresh_health
from atrium.doctor.synthesis_coherence import synthesis_coherence


def _archive(path, manifest_version, record_versions):
    lines = [
        json.dumps(
            {
                "kind": "rocket-agents-conversation-export",
                "schemaVersion": manifest_version,
                "records": len(record_versions),
            }
        )
    ]
    for position, version in enumerate(record_versions):
        lines.append(json.dumps({"schemaVersion": version, "id": f"conv-{position}", "events": []}))
    path.write_text("\n".join(lines) + "\n")
    return path


def test_a_manifest_may_not_outrank_the_records_under_it(tmp_path):
    # The live state on 2026-08-31: manifest version 2 over version 1 records.
    # A reader trusting the header assumes qualified event ids and finds
    # unqualified ones, and nothing reported it.
    archive = _archive(tmp_path / "archive.jsonl", 2, [1, 1, 2])
    finding = archive_schema_coherence(archive)
    assert finding.severity == "broken"
    assert finding.detail["older"] == 2


def test_a_coherent_archive_passes(tmp_path):
    archive = _archive(tmp_path / "archive.jsonl", 2, [2, 2])
    assert archive_schema_coherence(archive).severity == "ok"


def test_a_dead_refresh_is_broken_not_merely_stale(tmp_path):
    stamp = tmp_path / "last-refresh"
    stamp.write_text("1000")
    assert refresh_health(stamp, now=1000 + 60).severity == "ok"
    assert refresh_health(stamp, now=1000 + 7200).severity == "warn"
    # Eleven days is what actually happened to the sync orchestrator, and every
    # run still printed "done".
    assert refresh_health(stamp, now=1000 + 11 * 86400).severity == "broken"


def test_a_missing_refresh_stamp_is_broken(tmp_path):
    assert refresh_health(tmp_path / "absent").severity == "broken"


def test_a_missing_archive_is_broken(tmp_path):
    assert archive_freshness(tmp_path / "absent").severity == "broken"


def test_index_coverage_reports_the_gap_it_cannot_repair(tmp_path):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE records (conversation_id TEXT, provider TEXT)")
    connection.executemany(
        "INSERT INTO records VALUES (?, ?)",
        [("a", "codex"), ("b", "codex"), ("s", "synthesis")],
    )
    finding = index_coverage(connection, {"a", "b"})
    assert finding.severity == "ok"

    # A tenth of the corpus missing still answers every query confidently.
    finding = index_coverage(connection, {f"conv-{n}" for n in range(100)} | {"a", "b"})
    assert finding.severity == "broken"
    assert finding.detail["missing"] == 100


def test_synthesis_orphans_are_reported_never_deleted(tmp_path):
    records = tmp_path / "records"
    records.mkdir()
    (records / "one.json").write_text(json.dumps({"conversation_id": "gone", "episode_id": "e"}))
    finding = synthesis_coherence(tmp_path, {"present"})
    assert finding.severity == "warn"
    assert finding.detail["orphan_conversations"] == ["gone"]
    assert (records / "one.json").exists(), "paid model output is never removed by a check"


def test_read_archive_ids_skips_the_manifest(tmp_path):
    archive = _archive(tmp_path / "archive.jsonl", 2, [2, 2, 2])
    assert read_archive_ids(archive) == {"conv-0", "conv-1", "conv-2"}

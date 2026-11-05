"""The archive's age must follow whichever format is being written.

On 2026-11-05 the canonical archive moved to the v2 segment store. From then on
`archive.jsonl` is never written, so its mtime grows forever and status called a
healthy archive STALE, then (after a day) dead. The newest publication into the
active generation's segments is the write that counts; the v1 file still counts
too, so a rollback to v1 reads as fresh again.
"""

import json
import os
import time

from atrium.doctor.archive_freshness import archive_freshness

GENERATION = "a" * 64


def _segment_store(root, written_at):
    segments = root / "segments"
    published = segments / "generations" / f"g_{GENERATION}" / "segments"
    published.mkdir(parents=True)
    (segments / "current-generation.json").write_text(
        json.dumps({"generationId": GENERATION, "schemaVersion": 2})
    )
    os.utime(published, (written_at, written_at))
    return published


def _v1_archive(root, written_at):
    archive = root / "archive.jsonl"
    archive.write_text("{}\n")
    os.utime(archive, (written_at, written_at))
    return archive


def test_a_fresh_segment_store_beside_a_frozen_v1_file_is_fresh(tmp_path):
    now = time.time()
    archive = _v1_archive(tmp_path, now - 30 * 86400)
    _segment_store(tmp_path, now - 60)
    finding = archive_freshness(archive, now=now)
    assert finding.severity == "ok"
    assert finding.detail["age_seconds"] == 60


def test_a_segment_store_without_a_v1_file_is_not_missing(tmp_path):
    now = time.time()
    _segment_store(tmp_path, now - 60)
    finding = archive_freshness(tmp_path / "archive.jsonl", now=now)
    assert finding.severity == "ok"


def test_a_stopped_segment_store_still_reads_as_stale(tmp_path):
    now = time.time()
    _segment_store(tmp_path, now - 3 * 86400)
    finding = archive_freshness(tmp_path / "archive.jsonl", now=now)
    assert finding.severity == "broken"


def test_after_a_rollback_to_v1_the_v1_file_counts(tmp_path):
    now = time.time()
    archive = _v1_archive(tmp_path, now - 60)
    _segment_store(tmp_path, now - 30 * 86400)
    finding = archive_freshness(archive, now=now)
    assert finding.severity == "ok"
    assert finding.detail["age_seconds"] == 60


def test_no_archive_in_either_format_is_missing(tmp_path):
    finding = archive_freshness(tmp_path / "archive.jsonl", now=time.time())
    assert finding.code == "archive_missing"

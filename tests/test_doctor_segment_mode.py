"""In segment mode the doctor must not judge the index by the frozen v1 file.

After the 2026-11-05 cutover `archive.jsonl` stops moving. The first doctor run
on the segment store warned `index_coverage_drifting`, because the conversations
captured since the freeze are in the index and not in the v1 file. With a
segment inventory the generation check is the coverage check.
"""

import json
import time

from atrium.doctor.run_doctor import run_doctor
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _record(conversation_id):
    return Record(
        record_id=f"r-{conversation_id}",
        event_id=f"e-{conversation_id}",
        conversation_id=conversation_id,
        source_sha256="a" * 64,
        provider="claude-code",
        role="user",
        text="the sentinel body",
        authored_at="2026-11-05T10:00:00.000Z",
        workspace=None,
        title=None,
        event_index=0,
    )


def _setup(tmp_path):
    index = tmp_path / "index.sqlite3"
    connection = open_store(index)
    with connection:
        write_conversation(connection, "captured-after-freeze", [_record("captured-after-freeze")])
    connection.close()
    archive = tmp_path / "archive.jsonl"
    archive.write_text(json.dumps({"kind": "manifest"}) + "\n")
    stamp = tmp_path / "last-refresh"
    stamp.write_text(str(time.time()))
    return index, archive, stamp


def test_segment_mode_skips_the_checks_that_read_the_frozen_v1_file(tmp_path):
    index, archive, stamp = _setup(tmp_path)
    inventory = {"generationId": None, "pendingDeliveries": 0}
    checks = {
        finding.check
        for finding in run_doctor(index, archive, stamp, tmp_path / "registry", inventory)
    }
    assert "archive-generation" in checks
    assert "index-coverage" not in checks
    assert "archive-schema" not in checks
    assert "synthesis" not in checks


def test_without_an_inventory_the_v1_checks_still_run(tmp_path):
    index, archive, stamp = _setup(tmp_path)
    checks = {finding.check for finding in run_doctor(index, archive, stamp, tmp_path / "registry")}
    assert "index-coverage" in checks
    assert "archive-generation" not in checks

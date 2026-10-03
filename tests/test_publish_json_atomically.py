"""A status document is replaced whole or not at all."""

import json
import os

import pytest

from atrium.status import publish_json_atomically as module
from atrium.status.publish_json_atomically import publish_json_atomically


def test_the_document_lands_whole_and_leaves_no_temporary(tmp_path):
    target = tmp_path / "status" / "refresh.json"
    publish_json_atomically(target, {"schemaVersion": 1, "n": 1})
    publish_json_atomically(target, {"schemaVersion": 1, "n": 2})
    assert json.loads(target.read_text()) == {"schemaVersion": 1, "n": 2}
    assert [path.name for path in target.parent.iterdir()] == ["refresh.json"]


def test_the_temporary_shares_the_target_directory_and_is_fsynced(tmp_path, monkeypatch):
    """A rename is atomic only within one filesystem, and unsynced bytes can vanish."""
    target = tmp_path / "status" / "synthesis.json"
    synced = []
    real_fsync = os.fsync

    def recording_fsync(descriptor):
        synced.append(descriptor)
        real_fsync(descriptor)

    seen = []
    real_mkstemp = module.tempfile.mkstemp

    def recording_mkstemp(**kwargs):
        seen.append(kwargs["dir"])
        return real_mkstemp(**kwargs)

    monkeypatch.setattr(module.os, "fsync", recording_fsync)
    monkeypatch.setattr(module.tempfile, "mkstemp", recording_mkstemp)
    publish_json_atomically(target, {"schemaVersion": 1})
    assert seen == [target.parent]
    # Once for the file before the rename, once for the directory after it.
    assert len(synced) == 2


def test_a_failed_write_keeps_the_previous_document(tmp_path, monkeypatch):
    target = tmp_path / "refresh.json"
    publish_json_atomically(target, {"schemaVersion": 1, "n": 1})

    def failing_dump(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(module.json, "dump", failing_dump)
    with pytest.raises(OSError, match="disk full"):
        publish_json_atomically(target, {"schemaVersion": 1, "n": 2})
    assert json.loads(target.read_text()) == {"schemaVersion": 1, "n": 1}
    assert [path.name for path in tmp_path.iterdir()] == ["refresh.json"]

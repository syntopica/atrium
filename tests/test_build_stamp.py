"""An index must refuse code it was not built by, never silently serve it."""

import pytest

from atrium.store.build_versions import BUILD_VERSIONS
from atrium.store.open_store import open_store


def test_a_new_index_is_stamped_with_the_current_versions(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    stored = dict(connection.execute("SELECT key, value FROM build_metadata"))
    connection.close()
    assert stored == BUILD_VERSIONS


def test_reopening_with_the_same_versions_is_silent(tmp_path):
    path = tmp_path / "index.sqlite3"
    open_store(path).close()
    connection = open_store(path)
    connection.close()
    connection = open_store(path, read_only=True)
    connection.close()


def test_an_index_built_by_a_different_pipeline_refuses_to_open(tmp_path):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        connection.execute("UPDATE build_metadata SET value = 'older' WHERE key = 'pipeline'")
    connection.close()
    with pytest.raises(RuntimeError, match="different pipeline"):
        open_store(path)
    with pytest.raises(RuntimeError, match="different pipeline"):
        open_store(path, read_only=True)


def test_a_populated_unstamped_index_is_not_silently_adopted(tmp_path):
    """CREATE TABLE IF NOT EXISTS completes the schema on any database, so a
    writable open of a pre-versioning index would otherwise stamp legacy
    content as current -- laundering unknown-pipeline records."""
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        connection.execute(
            "INSERT INTO records (record_id, event_id, conversation_id, source_sha256,"
            " provider, role, text, event_index) VALUES ('r','e','c','s','p','user','legacy',0)"
        )
        connection.execute("DELETE FROM build_metadata")
    connection.close()
    with pytest.raises(RuntimeError, match="never stamped"):
        open_store(path)


def test_an_unstamped_index_refuses_read_only_opening(tmp_path):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        connection.execute("DELETE FROM build_metadata")
    connection.close()
    with pytest.raises(RuntimeError, match="never stamped"):
        open_store(path, read_only=True)


def test_a_transient_fault_is_never_answered_with_delete_and_re_ingest(tmp_path):
    """Deleting the index cannot fix a locked file, and an agent may act on it."""
    import sqlite3

    import pytest

    from atrium.store.verify_build_stamp import verify_build_stamp

    class Unreadable:
        def execute(self, *_):
            raise sqlite3.OperationalError("unable to open database file")

    with pytest.raises(sqlite3.OperationalError, match="unable to open database file"):
        verify_build_stamp(Unreadable(), stamp_if_empty=False)

    class Unversioned:
        def execute(self, *_):
            raise sqlite3.OperationalError("no such table: build_metadata")

    with pytest.raises(RuntimeError, match="predates index versioning"):
        verify_build_stamp(Unversioned(), stamp_if_empty=False)

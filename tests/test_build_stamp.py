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


def test_an_unstamped_index_refuses_read_only_opening(tmp_path):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        connection.execute("DELETE FROM build_metadata")
    connection.close()
    with pytest.raises(RuntimeError, match="never stamped"):
        open_store(path, read_only=True)

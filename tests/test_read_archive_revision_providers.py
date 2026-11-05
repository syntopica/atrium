"""The provider inventory lists each archive provider once, never synthesis."""

import sqlite3

from load_test_sql import load_test_sql

from atrium.store.read_archive_revision_providers import read_archive_revision_providers


def _archive() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(load_test_sql("archive_revision_providers/create_table"))
    connection.execute(load_test_sql("archive_revision_providers/create_index"))
    return connection


def test_each_archive_provider_appears_once_without_synthesis() -> None:
    connection = _archive()
    connection.executemany(
        load_test_sql("archive_revision_providers/insert_provider"),
        [("codex",), ("claude-code",), ("codex",), ("synthesis",), (None,), ("pi",)],
    )
    assert read_archive_revision_providers(connection) == {"claude-code", "codex", "pi"}


def test_an_empty_archive_has_no_providers() -> None:
    assert read_archive_revision_providers(_archive()) == set()

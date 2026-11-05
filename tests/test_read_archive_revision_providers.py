"""The provider inventory lists each archive provider once, never synthesis."""

import sqlite3

from atrium.store.read_archive_revision_providers import read_archive_revision_providers


def test_each_archive_provider_appears_once_without_synthesis() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE conversation_revisions (id INTEGER PRIMARY KEY, provider TEXT)"
    )
    connection.execute(
        "CREATE INDEX conversation_revisions_provider ON conversation_revisions (provider)"
    )
    connection.executemany(
        "INSERT INTO conversation_revisions (provider) VALUES (?)",
        [("codex",), ("claude-code",), ("codex",), ("synthesis",), (None,), ("pi",)],
    )
    assert read_archive_revision_providers(connection) == {"claude-code", "codex", "pi"}


def test_an_empty_archive_has_no_providers() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE conversation_revisions (id INTEGER PRIMARY KEY, provider TEXT)"
    )
    assert read_archive_revision_providers(connection) == set()

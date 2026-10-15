"""file-context finds the project's episodes that name one file, newest first."""

from atrium.ingest.record_identity import record_identity
from atrium.recall.file_episodes import file_episodes
from atrium.recall.file_phrase import file_phrase
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _episode(conversation, text, at, workspace="[HOME]/p/proj", role="synthesis"):
    return Record(
        record_identity(conversation, "e"),
        "e",
        conversation,
        "s",
        "synthesis",
        role,
        text,
        at,
        workspace,
        None,
        0,
    )


def test_a_file_name_is_one_quoted_phrase():
    assert file_phrase("atrium/context/retrieve_context.py") == '"retrieve_context.py"'
    assert file_phrase('odd"name.py') == '"odd""name.py"'


def test_a_generic_name_takes_its_directory_and_names_nothing_at_the_root():
    assert file_phrase("hooks/__init__.py") == '"hooks/__init__.py"'
    assert file_phrase("README.md") is None


def test_only_this_projects_episodes_naming_the_file_newest_first(tmp_path):
    connection = open_store(tmp_path / "index.sqlite3")
    rows = {
        "synthesis/old": _episode("synthesis/old", "Fixed cache.py expiry", "2026-09-01"),
        "synthesis/new": _episode("synthesis/new", "Reverted cache.py change", "2026-10-01"),
        "synthesis/other": _episode("synthesis/other", "cache.py", "2026-10-02", "[HOME]/p/x"),
        "raw": _episode("raw", "cache.py in a transcript", "2026-10-03", role="assistant"),
        "synthesis/miss": _episode("synthesis/miss", "Changed cache.ts", "2026-10-04"),
    }
    with connection:
        for conversation, row in rows.items():
            write_conversation(connection, conversation, [row])
    hits = file_episodes(connection, "[HOME]/p/proj", '"cache.py"', 5)
    connection.close()
    assert [hit.conversation_id for hit in hits] == ["synthesis/new", "synthesis/old"]

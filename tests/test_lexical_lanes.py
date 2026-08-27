"""The two lexical lanes answer different questions and must not be merged."""

from atrium.record import Record
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store
from atrium.store.write_records import rebuild_lexical_lanes, write_records


def _record(record_id, text):
    return Record(
        record_id=record_id,
        conversation_id="c",
        source_sha256="s",
        provider="test",
        role="user",
        text=text,
        authored_at="2026-08-25T00:00:00Z",
        workspace=None,
        title=None,
        event_index=0,
    )


def _store(tmp_path, records):
    connection = open_store(tmp_path / "index.sqlite3")
    write_records(connection, records)
    rebuild_lexical_lanes(connection)
    return connection


def test_word_lane_does_not_match_a_longer_word(tmp_path):
    """`WAL` must not retrieve `wall`. On the previous system's trigram-only index
    this query returned nine `wall...` false positives and ranked the first exact
    hit seventh."""
    connection = _store(
        tmp_path,
        [
            _record("wal", "The WAL journal mode was reverted after thirteen SIGBUS crashes."),
            _record("wall", "We painted the wall, the wallpaper and the walled garden."),
        ],
    )
    hits = search_words(connection, "WAL")
    assert [hit.record_id for hit in hits] == ["wal"]


def test_substring_lane_still_finds_fragments(tmp_path):
    """The substring behaviour is not deleted, it is moved to the lane that wants it."""
    connection = _store(tmp_path, [_record("wall", "the walled garden")])
    rows = connection.execute(
        "SELECT r.record_id FROM substrings JOIN records r ON r.rowid = substrings.rowid "
        "WHERE substrings MATCH 'wal'"
    ).fetchall()
    assert [row[0] for row in rows] == ["wall"]


def test_punctuation_in_a_query_is_not_fts_syntax(tmp_path):
    """`memstore_delete_drawers()` is a search, not an FTS5 parse error."""
    connection = _store(tmp_path, [_record("fn", "call memstore_delete_drawers to remove them")])
    hits = search_words(connection, "memstore_delete_drawers()")
    assert [hit.record_id for hit in hits] == ["fn"]


def test_every_hit_names_the_lane_that_found_it(tmp_path):
    """Fusion is never allowed to be the only output, so lane is not optional."""
    connection = _store(tmp_path, [_record("a", "a record about retrieval and memory")])
    assert search_words(connection, "retrieval")[0].lane == "words"

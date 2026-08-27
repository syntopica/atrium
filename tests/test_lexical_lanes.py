"""The two lexical lanes answer different questions and must not be merged."""

from atrium.record import Record
from atrium.retrieve.search_words import search_words
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation


def _record(record_id, text):
    return Record(
        record_id=record_id,
        event_id=record_id,
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
    with connection:
        write_conversation(connection, "c", records)
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
    """`mempalace_delete_drawers()` is a search, not an FTS5 parse error."""
    connection = _store(tmp_path, [_record("fn", "call mempalace_delete_drawers to remove them")])
    hits = search_words(connection, "mempalace_delete_drawers()")
    assert [hit.record_id for hit in hits] == ["fn"]


def test_every_hit_names_the_lane_that_found_it(tmp_path):
    """Fusion is never allowed to be the only output, so lane is not optional."""
    connection = _store(tmp_path, [_record("a", "a record about retrieval and memory")])
    assert search_words(connection, "retrieval")[0].lane == "words"


def test_a_version_query_finds_the_version(tmp_path):
    """`3.7.0` must not return nothing. The index tokenizer splits on punctuation,
    so the query becomes a phrase over the adjacent tokens instead of being
    dropped -- this lane exists for versions, identifiers and names."""
    connection = _store(
        tmp_path,
        [
            _record("ver", "the fork is pinned to mempalace 3.7.0 for now"),
            _record("apart", "we tried 3 approaches, 7 failures and 0 regressions"),
        ],
    )
    hits = search_words(connection, "3.7.0")
    assert [hit.record_id for hit in hits] == ["ver"]


def test_a_version_query_rejects_the_same_tokens_separated_by_spaces(tmp_path):
    """An FTS5 phrase preserves token order but not the punctuation between
    tokens, so `3.7.0` also matched `allocate 3 7 0 workers`. The adjacency
    filter requires the parts to be joined by punctuation in the stored text."""
    connection = _store(
        tmp_path,
        [
            _record("ver", "the fork is pinned to mempalace 3.7.0 for now"),
            _record("shift", "allocate 3 7 0 workers across shifts"),
        ],
    )
    hits = search_words(connection, "3.7.0")
    assert [hit.record_id for hit in hits] == ["ver"]


def test_a_snake_case_identifier_still_matches_through_the_adjacency_filter(tmp_path):
    """`_` is a \\w character, so a separator class of bare `[^\\w\\s]+` would
    silently drop every snake_case hit. The identifier query keeps working."""
    connection = _store(
        tmp_path,
        [
            _record("fn", "call mempalace_delete_drawers to remove them"),
            _record("spaced", "mempalace delete drawers one at a time"),
        ],
    )
    hits = search_words(connection, "mempalace_delete_drawers")
    assert [hit.record_id for hit in hits] == ["fn"]


def test_a_punctuated_term_next_to_a_plain_word_keeps_or_semantics(tmp_path):
    """Terms are OR-ed. A hit that fails the adjacency check may still have
    matched a plain word the filter cannot see, so mixed queries do not filter."""
    connection = _store(
        tmp_path,
        [
            _record("prose", "the retrieval layer was rebuilt yesterday"),
            _record("shift", "allocate 3 7 0 workers across shifts"),
        ],
    )
    hits = search_words(connection, "retrieval 3.7.0")
    assert "prose" in [hit.record_id for hit in hits]


def test_a_hyphenated_model_name_is_not_truncated(tmp_path):
    connection = _store(tmp_path, [_record("m", "we benchmarked GPT-5.3 against the others")])
    assert [hit.record_id for hit in search_words(connection, "GPT-5.3")] == ["m"]


def test_the_adjacency_filter_keeps_diacritic_insensitive_hits(tmp_path):
    """The index tokenizer removes diacritics, so `café-au-lait` finds a stored
    `cafe-au-lait`; a verifier comparing raw strings threw that hit away."""
    connection = _store(tmp_path, [_record("c", "we ordered a cafe-au-lait at the bar")])
    assert [h.record_id for h in search_words(connection, "café-au-lait")] == ["c"]


def test_the_adjacency_filter_survives_a_wall_of_false_candidates(tmp_path):
    """With 60 spaced `3 7 0` rows outranking the one real `3.7.0`, a fixed
    prefetch returned nothing; the filter must paginate until it verifies."""
    decoys = [
        _record(f"spaced-{i:02d}", f"allocate 3 7 0 workers across shifts run {i}")
        for i in range(60)
    ]
    connection = _store(tmp_path, [*decoys, _record("ver", "pinned to mempalace 3.7.0 for now")])
    assert [h.record_id for h in search_words(connection, "3.7.0")] == ["ver"]


def test_a_query_of_only_punctuation_returns_nothing_rather_than_raising(tmp_path):
    connection = _store(tmp_path, [_record("a", "some ordinary prose about retrieval")])
    assert search_words(connection, "...") == []

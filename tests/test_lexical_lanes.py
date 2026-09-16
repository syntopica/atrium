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
    """`memstore_delete_drawers()` is a search, not an FTS5 parse error."""
    connection = _store(tmp_path, [_record("fn", "call memstore_delete_drawers to remove them")])
    hits = search_words(connection, "memstore_delete_drawers()")
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
            _record("ver", "the fork is pinned to memstore 3.7.0 for now"),
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
            _record("ver", "the fork is pinned to memstore 3.7.0 for now"),
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
            _record("fn", "call memstore_delete_drawers to remove them"),
            _record("spaced", "memstore delete drawers one at a time"),
        ],
    )
    hits = search_words(connection, "memstore_delete_drawers")
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
    connection = _store(tmp_path, [*decoys, _record("ver", "pinned to memstore 3.7.0 for now")])
    assert [h.record_id for h in search_words(connection, "3.7.0")] == ["ver"]


def test_a_query_of_only_punctuation_returns_nothing_rather_than_raising(tmp_path):
    connection = _store(tmp_path, [_record("a", "some ordinary prose about retrieval")])
    assert search_words(connection, "...") == []


def test_a_scope_narrows_before_the_limit_not_after(tmp_path):
    """Filtering returned hits would ask for the global top N and discard it.

    The scoped project's records rank *below* sixty others here, so a lane that
    took its limit first and filtered afterwards would answer nothing.
    """
    from atrium.record import Record
    from atrium.retrieve.search_words import search_words
    from atrium.store.open_store import open_store
    from atrium.store.write_conversation import write_conversation

    def record(index, workspace, text):
        return Record(
            record_id=f"r{index}",
            event_id=f"e{index}",
            conversation_id=f"c{index}",
            source_sha256=f"s{index}",
            provider="claude-code",
            role="user",
            text=text,
            authored_at="2026-08-01T00:00:00Z",
            workspace=workspace,
            title=None,
            event_index=0,
        )

    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        for index in range(60):
            write_conversation(
                connection, f"c{index}", [record(index, "[HOME]/p/other", "sentinel sentinel")]
            )
        write_conversation(
            connection, "c60", [record(60, "[HOME]/p/mine", "sentinel mentioned once")]
        )

    assert len(search_words(connection, "sentinel", 5)) == 5
    scoped = search_words(connection, "sentinel", 5, "[HOME]/p/mine")
    connection.close()
    assert [hit.record_id for hit in scoped] == ["r60"]


def test_the_narrow_pass_ranks_a_record_holding_every_term_first(tmp_path):
    """AND before OR: the intersection is both cheaper and the better answer.

    The measurement that put it there is in `conjunctive_expression`; this fixes
    the semantics, which is that a record matching every term outranks a record
    matching one, whatever bm25 makes of a two-record corpus.
    """
    connection = _store(
        tmp_path,
        [
            _record("one", "the stop hook fires on a status turn"),
            _record("two", "status " * 200),
        ],
    )
    hits = search_words(connection, "stop hook status", limit=2)
    assert [hit.record_id for hit in hits] == ["one", "two"]


def test_the_broad_pass_still_answers_when_no_record_holds_every_term(tmp_path):
    connection = _store(
        tmp_path,
        [_record("one", "a stop hook"), _record("two", "a status turn")],
    )
    hits = search_words(connection, "hook turn", limit=5)
    assert sorted(hit.record_id for hit in hits) == ["one", "two"]


def test_an_exhausted_budget_is_reported_rather_than_read_as_an_empty_index(tmp_path):
    """An empty result must never be indistinguishable from "nothing indexed"."""
    import sqlite3

    from atrium.retrieve.bounded_rows import bounded_rows

    connection = _store(tmp_path, [_record("one", "a stop hook")])
    exhausted: set[str] = set()
    # A statement long enough to reach the progress handler at all: the check
    # runs every 10,000 virtual-machine instructions, so a one-row query beats
    # any deadline by finishing first.
    spin = """
        WITH RECURSIVE counter(n) AS (
            SELECT 1 UNION ALL SELECT n + 1 FROM counter WHERE n < ?
        )
        SELECT count(*) FROM counter
    """
    rows = bounded_rows(connection, spin, (10_000_000,), exhausted, 1)
    assert rows == []
    assert exhausted == {"lexical_budget_exhausted"}
    # The connection survives the interruption and still answers.
    assert connection.execute("SELECT count(*) FROM records").fetchone() == (1,)
    assert isinstance(connection, sqlite3.Connection)


def test_a_broken_index_is_not_reported_as_a_spent_budget(tmp_path):
    """Every OperationalError used to be swallowed as "ran out of time"."""
    import sqlite3

    import pytest

    from atrium.retrieve.bounded_rows import bounded_rows

    connection = _store(tmp_path, [_record("one", "a stop hook")])
    exhausted: set[str] = set()
    with pytest.raises(sqlite3.OperationalError):
        bounded_rows(connection, "SELECT * FROM a_table_that_is_not_here", (), exhausted)
    assert exhausted == set()


def test_an_all_punctuated_query_also_asks_the_narrow_question_first(tmp_path):
    """The verifier branch kept the unbounded OR path when the plain one stopped."""
    connection = _store(
        tmp_path,
        [
            _record("both", "shipping 3.7.0 beside claude-opus-5 in one line"),
            _record("one", "claude-opus-5 " * 50),
        ],
    )
    hits = search_words(connection, "3.7.0 claude-opus-5", limit=2)
    assert [hit.record_id for hit in hits] == ["both", "one"]

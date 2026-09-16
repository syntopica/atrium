"""The broad expression drops what the whole corpus says, and nothing else."""

from atrium.record import Record
from atrium.retrieve.selective_expression import selective_expression
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
        authored_at="2026-09-16T00:00:00Z",
        workspace=None,
        title=None,
        event_index=0,
    )


def _corpus(tmp_path, count):
    connection = open_store(tmp_path / "index.sqlite3")
    with connection:
        records = [_record(f"common-{number}", "the meeting notes") for number in range(count)]
        records.append(_record("rare", "the vault rotation"))
        write_conversation(connection, "c", records)
    return connection


def test_a_term_the_corpus_repeats_is_dropped(tmp_path):
    connection = _corpus(tmp_path, 200)
    total = connection.execute("SELECT count(*) FROM records").fetchone()[0]
    assert selective_expression(connection, "words", "the vault", total) == '"vault"'


def test_all_terms_survive_when_all_of_them_are_common(tmp_path):
    """A query made only of frequent words still has to be asked. Dropping every
    term would turn it into an empty expression, which retrieves nothing at all
    and reads as "the index knows nothing about this"."""
    connection = _corpus(tmp_path, 200)
    total = connection.execute("SELECT count(*) FROM records").fetchone()[0]
    assert selective_expression(connection, "words", "the meeting", total) == '"the" OR "meeting"'

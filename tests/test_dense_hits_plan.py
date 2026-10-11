"""The in-index dense scan must start from the vectors, not from every record."""

from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export
from load_test_sql import load_test_sql

from atrium.context.context_scope import context_scope
from atrium.sql.load_sql import load_sql


def test_the_dense_scan_is_driven_from_vectors(corpus):
    # Driven from records it read all 1.86M rows to test their role: 213 s
    # unscoped on the live index (2026-10-11), against 0.6 s from vectors.
    connection, project, _, _ = corpus
    for curated, workspace in ((False, None), (False, str(project)), (True, None)):
        scope, parameters = context_scope(curated, workspace)
        statement = load_test_sql("context_indexes/explain_statement").format(
            statement=load_sql("context/dense_hits").format(scope=scope)
        )
        plan = [row[3] for row in connection.execute(statement, parameters).fetchall()]
        assert plan[0].startswith("SCAN v"), plan

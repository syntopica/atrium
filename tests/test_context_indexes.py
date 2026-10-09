"""Derived acceleration must never mutate canonical evidence rows."""

import json

from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export
from load_test_sql import load_test_sql

from atrium.context.context_index_specs import context_index_specs
from atrium.context.context_indexes_ready import context_indexes_ready
from atrium.context.context_scope import context_scope
from atrium.context.ensure_context_indexes import ensure_context_indexes
from atrium.context.retrieve_context import retrieve_context


def test_context_indexes_are_covering_and_idempotent(corpus):
    connection, project, _, _ = corpus
    before = connection.execute(load_test_sql("select_all_records")).fetchall()
    changes = connection.total_changes
    for _ in range(2):
        ensure_context_indexes(connection)
    assert context_indexes_ready(connection)
    assert connection.total_changes == changes
    assert connection.execute(load_test_sql("select_all_records")).fetchall() == before
    for curated in (True, False):
        scope, params = context_scope(curated, str(project))
        plan = connection.execute(
            load_test_sql("context_indexes/explain_scoped_records").format(scope=scope),
            params,
        ).fetchall()
        assert any("COVERING INDEX records_context" in row[3] for row in plan)
        assert not any(row[3] == "SCAN r" for row in plan)


def test_missing_context_indexes_do_not_trigger_read_side_mutation(corpus):
    connection, project, state, _ = corpus
    for name in context_index_specs():
        connection.execute(load_test_sql("context_indexes/drop_index").format(name=name))
    before = connection.total_changes
    result = retrieve_context(connection, "Server-a", project=project, state=state, lane="words")
    assert "context_indexes_missing_run_prepare_context" in result["warnings"]
    assert result["degraded"]
    assert not context_indexes_ready(connection)
    assert connection.total_changes == before


def test_prepare_context_command_preserves_rows(corpus, capsys):
    from atrium.cli import main

    connection, _, _, index = corpus
    before = connection.execute(load_test_sql("select_all_records")).fetchall()
    for name in context_index_specs():
        connection.execute(load_test_sql("context_indexes/drop_index").format(name=name))
    connection.commit()
    assert main(["--index", str(index), "prepare-context", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["records_before"] == result["records_after"]
    assert result["already_ready"] is False
    assert main(["--index", str(index), "prepare-context", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["already_ready"] is True
    assert connection.execute(load_test_sql("select_all_records")).fetchall() == before


def test_workspace_range_matches_only_root_and_descendants(corpus):
    connection, project, _, _ = corpus
    scope, params = context_scope(False, str(project))
    for value, expected in [
        (str(project), True),
        (str(project) + "/nested", True),
        (str(project) + "-other", False),
        (str(project) + "2", False),
    ]:
        row = connection.execute(
            load_test_sql("context_indexes/match_workspace_scope").format(scope=scope),
            (value, *params),
        ).fetchone()
        assert bool(row) == expected

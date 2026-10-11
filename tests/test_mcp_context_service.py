"""The MCP context tool asks the resident service first, as the CLI does."""

import pytest
from mcp.server.mcpserver.exceptions import ToolError

import atrium.adapters.atrium_context as adapter


@pytest.fixture
def sent(monkeypatch, tmp_path):
    monkeypatch.setattr(adapter, "state_directory", lambda: tmp_path)
    monkeypatch.setattr(adapter, "INDEX", tmp_path / "index.sqlite3")
    return []


@pytest.mark.parametrize("project", [".", "~/repo"])
def test_a_served_answer_is_returned_with_an_absolute_project(monkeypatch, sent, tmp_path, project):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))

    def service(_socket, request, _timeout):
        sent.append(request)
        return {"served": True}

    monkeypatch.setattr(adapter, "request_context_service", service)
    assert adapter.atrium_context("x", project=project) == {"served": True}
    assert sent[0]["project"].startswith("/")
    assert "~" not in sent[0]["project"]


@pytest.mark.parametrize("reply", [None, {"error": "index_mismatch"}, OSError()])
def test_without_a_usable_service_it_retrieves_in_process(monkeypatch, sent, reply):
    def service(_socket, _request, _timeout):
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(adapter, "request_context_service", service)
    result = adapter.atrium_context("x")
    assert result["index_status"] == "unavailable"


def test_a_stalled_service_is_reported_not_retried(monkeypatch, sent):
    def service(_socket, _request, _timeout):
        raise TimeoutError

    def in_process(*_args, **_kwargs):
        raise AssertionError("a stalled service must not start in-process retrieval")

    monkeypatch.setattr(adapter, "request_context_service", service)
    monkeypatch.setattr(adapter, "context_from_index", in_process)
    result = adapter.atrium_context("x")
    assert "context_service_timeout" in result["warnings"]


@pytest.mark.parametrize(("query", "project"), [(" ", None), ("x", "/")])
def test_a_caller_error_is_reported_even_when_the_service_stalls(monkeypatch, sent, query, project):
    def service(_socket, _request, _timeout):
        raise TimeoutError

    monkeypatch.setattr(adapter, "request_context_service", service)
    with pytest.raises(ToolError):
        adapter.atrium_context(query, project=project)

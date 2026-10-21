"""Synthetic secrets never leave note ingestion or retrieval rendering."""

import asyncio
import json

import pytest

from atrium.context.render_evidence import render_evidence
from atrium.context.render_hit import render_hit
from atrium.ingest.to_note_records import to_note_records
from atrium.retrieve.hit import Hit
from atrium.session.redact_sensitive_text import redact_sensitive_text


@pytest.mark.parametrize(
    "text",
    [
        "| Password | `synthetic-canary` |",
        "| **Contraseña** | synthetic-canary |",
        "| Service | Password |\n| --- | --- |\n| Mail | synthetic-canary |",
        "| Service | API key |\n| --- | --- |\n| Mail | `synthetic-canary` |",
        "| Password | x |",
        r"| Password | synthetic-canary\|tail |",
    ],
)
def test_table_values_are_redacted(text):
    sanitized = redact_sensitive_text(text)
    assert "synthetic-canary" not in sanitized
    assert "[REDACTED:secret]" in sanitized
    assert redact_sensitive_text(sanitized) == sanitized


def test_nonsecret_tables_are_unchanged():
    text = "| Policy | Owner |\n| --- | --- |\n| Password rotation | Example |"
    assert redact_sensitive_text(text) == text


def test_full_hit_is_redacted_before_excerpting_and_ingestion():
    text = "# Synthetic\n\n| Password | synthetic-canary |"
    hit = Hit("id", text, 1.0, "words", "brain/synthetic.md", "a" * 64, None, "brain", "note")
    assert "synthetic-canary" not in json.dumps(render_hit(hit))
    for budget in [3, 15, 1000]:
        item = render_evidence(hit, "synthetic-canary", budget, "direct", None)
        assert item["text"] not in {"canary", "synthetic-canary"}
        assert "synthetic-canary" not in json.dumps(item)
        assert len(item["text"]) <= budget
        assert item["excerpt_basis"] == "redacted_text"
        assert (
            item["text"] == redact_sensitive_text(text)[item["excerpt_start"] : item["excerpt_end"]]
        )
    records = list(
        to_note_records({"path": "brain/synthetic.md", "text": text, "sha256": "a" * 64})
    )
    assert all("synthetic-canary" not in record.text for record in records)
    assert all(record.source_sha256 == "a" * 64 for record in records)
    assert hit.text == text


@pytest.mark.parametrize("served", [True, False])
def test_resident_mcp_serializations_are_redacted(monkeypatch, tmp_path, served):
    import atrium.adapters.atrium_context as adapter
    from atrium.adapters.mcp_app import MCP

    monkeypatch.setattr(adapter, "state_directory", lambda: tmp_path)
    monkeypatch.setattr(
        adapter,
        "request_context_service",
        lambda *_: {
            "index_status": "ready",
            "steps": [],
            "evidence": [
                {"text": "| Password | synthetic-canary |", "truncated": False},
                {"text": "unlabelled-canary", "truncated": True},
            ],
        },
    )
    if not served:
        response = adapter.request_context_service(None, None, None)
        monkeypatch.setattr(adapter, "request_context_service", lambda *_: None)
        monkeypatch.setattr(adapter, "context_from_index", lambda *_args, **_kwargs: response)
        monkeypatch.setattr(adapter, "resident_reranker", lambda: None)
    result = asyncio.run(MCP.call_tool("atrium_context", {"query": "synthetic"}))
    assert result.content
    assert result.structured_content is not None
    rendered = result.model_dump_json()
    assert "synthetic-canary" not in rendered
    assert "unlabelled-canary" not in rendered
    assert "[REDACTED:" in rendered


def test_resident_cli_and_response_budget(monkeypatch, tmp_path, capsys):
    from atrium.context import run_context_cli as module
    from atrium.context.sanitize_context_response import sanitize_context_response

    original = {
        "index_status": "ready",
        "steps": [],
        "text_chars": 40,
        "evidence": [{"text": "| Password | tiny |", "truncated": False}],
    }
    monkeypatch.setattr(module, "request_context_service", lambda *_: original)
    assert module.run_context_cli(tmp_path / "unused", "q", None, 4, 100, "words", tmp_path) == 0
    result = json.loads(capsys.readouterr().out)
    assert "tiny" not in result["evidence"][0]["text"]
    assert result["text_chars"] == len(result["evidence"][0]["text"])
    assert result["text_chars"] <= len(original["evidence"][0]["text"])
    assert result["evidence"][0]["excerpt_start"] is None
    assert original["evidence"][0]["text"] == "| Password | tiny |"
    assert sanitize_context_response(result) == result


def test_search_file_context_and_injection_use_full_redaction(monkeypatch, tmp_path, capsys):
    from unittest.mock import Mock

    from atrium.commands import run_search as search_module
    from atrium.recall import run_file_context_cli as file_module
    from atrium.recall.render_snapshot import render_snapshot

    hit = Hit(
        "id",
        "| Password | synthetic-canary |",
        1.0,
        "words",
        "synthetic",
        "a" * 64,
        None,
        "brain",
        "note",
    )
    assert "synthetic-canary" not in render_snapshot("synthetic", [hit])
    monkeypatch.setattr(search_module, "open_store", lambda *_args, **_kwargs: Mock())
    monkeypatch.setattr(search_module, "read_record_hosts", lambda *_: {})
    monkeypatch.setattr("atrium.retrieve.search.search", lambda *_args, **_kwargs: [hit])
    assert search_module.run_search(tmp_path / "unused", "q", 1, "words") == 0
    assert "synthetic-canary" not in capsys.readouterr().out
    monkeypatch.setattr(file_module, "repository_root", lambda _: tmp_path)
    monkeypatch.setattr(file_module, "project_workspace", lambda _: "synthetic")
    monkeypatch.setattr(file_module, "open_store", lambda *_args, **_kwargs: Mock())
    monkeypatch.setattr(file_module, "file_episodes", lambda *_: [hit])
    monkeypatch.setattr(file_module, "read_supersessions", lambda *_: {})
    assert file_module.run_file_context_cli(tmp_path / "unused", tmp_path / "file", 1) == 0
    assert "synthetic-canary" not in capsys.readouterr().out


def test_whole_hit_optional_title_is_sanitized():
    from dataclasses import make_dataclass

    titled_hit = make_dataclass(
        "TitledHit", [("title", str)], bases=(Hit,), frozen=True, kw_only=True
    )
    hit = titled_hit(
        "id",
        "ordinary text",
        1.0,
        "words",
        "synthetic",
        "a" * 64,
        None,
        "brain",
        title="password: synthetic-title-canary",
    )
    assert "synthetic-title-canary" not in json.dumps(render_hit(hit))
    assert hit.title == "password: synthetic-title-canary"

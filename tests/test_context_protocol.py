"""A real CLI and a fresh MCP process must expose the same safe evidence."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from context_protocol_fixture import context_protocol_fixture


def test_context_cli_and_fresh_mcp_agree(tmp_path):
    pytest.importorskip("mcp")
    from context_protocol_exchange import context_protocol_exchange

    fixture = context_protocol_fixture(tmp_path)
    env = {
        **os.environ,
        "ATRIUM_INDEX": fixture["index"],
        "ATRIUM_STATE": fixture["state"],
        "SYNTOPICA_DATA": fixture["instance"],
    }
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "atrium.cli",
            "--index",
            fixture["index"],
            "context",
            "Atlas mail",
            "--project",
            fixture["project"],
            "--lane",
            "words",
            "--max-chars",
            "4000",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert cli.returncode == 0, cli.stderr
    result = json.loads(cli.stdout)
    exchange = asyncio.run(context_protocol_exchange(env, fixture["project"]))
    mcp = exchange["context"]
    assert not mcp.is_error
    assert mcp.structured_content["evidence"] == result["evidence"]
    text = "\n".join(item["text"] for item in result["evidence"])
    assert "ORBIT-42" in text
    assert "250 response" in text
    assert "routes remotely" in text
    assert "UNRELATED_HISTORY_SENTINEL" not in text
    assert "DELIVERED_WITHOUT_EVIDENCE" not in text
    assert result["requires_live_verification"] is True
    assert result["text_chars"] <= 4000
    assert all(item["record_id"] and item["source_sha256"] for item in result["evidence"])
    assert exchange["tool"].annotations.read_only_hint is True
    assert exchange["invalid"].is_error
    source = exchange["legacy"].structured_content["result"][0]
    assert source["role"] == "source"
    assert source["trust"] == "untrusted"

"""Only servers the codex config declares are switched off."""

from atrium.synthesize.codex_mcp_overrides import codex_mcp_overrides


def test_each_declared_server_is_disabled(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[mcp_servers.serena]\ncommand = "serena"\nrequired = true\n\n'
        '[mcp_servers.context7]\nurl = "https://example.invalid"\n'
    )
    assert codex_mcp_overrides(tmp_path) == [
        "-c",
        "mcp_servers.serena.enabled=false",
        "-c",
        "mcp_servers.context7.enabled=false",
    ]


def test_a_config_without_servers_adds_nothing(tmp_path):
    (tmp_path / "config.toml").write_text('model = "x"\n')
    assert codex_mcp_overrides(tmp_path) == []


def test_a_missing_config_adds_nothing(tmp_path):
    assert codex_mcp_overrides(tmp_path) == []

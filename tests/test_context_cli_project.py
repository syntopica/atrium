"""The CLI hands the context service an absolute project, never a relative one."""

import os
from pathlib import Path

from atrium.context import run_context_cli as module


def test_a_relative_project_reaches_the_service_resolved(tmp_path, monkeypatch, capsys):
    sent = {}

    def served(socket_path, request, timeout):
        sent.update(request)
        return {"index_status": "ready", "evidence": [], "steps": []}

    monkeypatch.setattr(module, "request_context_service", served)
    monkeypatch.chdir(tmp_path)
    code = module.run_context_cli(
        tmp_path / "index.sqlite3", "q", Path(), 4, 1400, "dense", tmp_path
    )
    assert code == 0
    assert sent["project"] == os.path.realpath(tmp_path)
    assert '"served_by": "service"' in capsys.readouterr().out

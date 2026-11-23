import socket
from pathlib import Path

import pytest

from atrium.serve.context_socket_path import context_socket_path


def test_a_short_state_directory_keeps_the_socket_beside_the_index() -> None:
    assert context_socket_path(Path("/w/atrium")) == Path("/w/atrium/context.sock")


def test_a_deep_state_directory_gets_a_bindable_socket_of_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = Path("/tmp") / f"atrium-home-{tmp_path.name}"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    deep = Path("/" + "d" * 120) / "atrium"
    path = context_socket_path(deep)
    try:
        assert path.parent == home / ".cache" / "atrium"
        assert path == context_socket_path(deep)
        assert path != context_socket_path(deep.parent / "other")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        listener.close()
    finally:
        path.unlink(missing_ok=True)
        path.parent.rmdir()
        path.parent.parent.rmdir()
        home.rmdir()

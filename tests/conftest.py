"""Keep every test away from the machine's own conversation-writer state."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_writer_state(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Point the freeze sentinel at an empty directory.

    Doctor, status and recall read the real sentinel by default, so a migration
    freeze on the machine running the suite would turn every "stays quiet"
    assertion red.
    """
    state = tmp_path_factory.mktemp("writer-state")
    monkeypatch.setenv("ROCKET_AGENTS_CONVERSATION_STATE", str(state))
    return state

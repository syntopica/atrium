"""Where the conversation writers' migration freeze sentinel lives."""

import os
from collections.abc import Mapping
from pathlib import Path


def freeze_sentinel_path(
    environ: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """Resolve the sentinel the same way dotfiles and scribe do.

    ``$ROCKET_AGENTS_CONVERSATION_STATE/migration.freeze``, or the default state
    directory under the home directory. An empty variable counts as unset. A
    relative one makes every writer refuse to start, so nothing could be frozen
    under it and the default path is the one worth reporting.
    """
    env = os.environ if environ is None else environ
    declared = env.get("ROCKET_AGENTS_CONVERSATION_STATE", "")
    if declared and Path(declared).is_absolute():
        return Path(declared) / "migration.freeze"
    base = Path.home() if home is None else home
    return base / ".local/state/rocket-agents/conversations/migration.freeze"

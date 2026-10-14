"""The one place that decides where the forget ledger lives."""

import os
from collections.abc import Mapping
from pathlib import Path

from atrium.state.instance_directory import instance_directory
from atrium.state.read_section_path import read_section_path


def forget_ledger_file(environ: Mapping[str, str] | None = None, cwd: Path | None = None) -> Path:
    """Resolve the ledger file, most explicit source first.

    The ledger is policy, not derived state: it is tracked in the instance
    repository (``forget.path``, default ``forget/``) so every machine that
    serves the instance forgets the same records, and rebuilding the index
    cannot bring a forgotten record back. ``ATRIUM_STATE`` names a second index
    on purpose, so it gets a ledger of its own beside it.
    """
    env = os.environ if environ is None else environ
    explicit = env.get("ATRIUM_STATE")
    if explicit:
        return Path(explicit).expanduser().resolve() / "forget" / "ledger.jsonl"
    data = instance_directory(env, cwd)
    if data is not None:
        return read_section_path(data, "forget", "forget") / "ledger.jsonl"
    return Path.home() / ".atrium" / "forget" / "ledger.jsonl"

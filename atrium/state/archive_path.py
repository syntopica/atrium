"""Where the canonical conversation archive is, for the instance being served."""

import os
from collections.abc import Mapping
from pathlib import Path

from atrium.state.instance_directory import instance_directory
from atrium.state.read_section_path import read_section_path

ARCHIVE_NAME = "archive.jsonl"


def archive_path(
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
) -> Path:
    """The archive under the instance's ``conversations.path``, else the old home path.

    The archive is layer 1 and rocket-agents writes it; Atrium only reads it.
    It lives in the data directory for the same reason the index does -- a
    data directory exists so that nothing the instance depends on is scattered
    under the home directory -- and the fallback keeps a machine that has no
    instance reading the path the export used before 2026-09-16.
    """
    env = os.environ if environ is None else environ
    data = instance_directory(env, cwd)
    if data is not None:
        return read_section_path(data, "conversations", "conversations") / ARCHIVE_NAME
    base = Path.home() if home is None else home
    return base / ".local" / "share" / "rocket-agents" / "conversations" / ARCHIVE_NAME

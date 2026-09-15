"""The one place that decides where Atrium's rebuildable state lives."""

import os
from collections.abc import Mapping
from pathlib import Path

from atrium.state.find_data_directory import find_data_directory
from atrium.state.read_atrium_path import read_atrium_path


def state_directory(
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the state directory, most explicit source first.

    1. ``ATRIUM_STATE``: the directory itself, for a second index on purpose.
    2. ``SYNTOPICA_DATA``: an instance; its ``atrium.path`` is the answer.
    3. The instance enclosing the working directory, if any.
    4. ``~/.atrium``, where the index lived before instances existed.

    Instance data belongs in the data directory: a `syntopica.config.json`
    exists so that everything derived from it sits beside it, and an index
    that lives under the home directory is invisible to the doctor of the
    instance it serves. The last rule keeps a machine with no instance working.
    """
    env = os.environ if environ is None else environ
    explicit = env.get("ATRIUM_STATE")
    if explicit:
        return Path(explicit).expanduser().resolve()
    data = env.get("SYNTOPICA_DATA")
    if data:
        return read_atrium_path(Path(data).expanduser().resolve())
    found = find_data_directory(Path.cwd() if cwd is None else cwd)
    if found is not None:
        return read_atrium_path(found)
    return (Path.home() if home is None else home) / ".atrium"

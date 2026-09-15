"""The one place that decides where Atrium's rebuildable state lives."""

import os
from collections.abc import Mapping
from pathlib import Path

from atrium.state.instance_directory import instance_directory
from atrium.state.read_section_path import read_section_path


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
    data = instance_directory(env, cwd)
    if data is not None:
        return read_section_path(data, "atrium", "atrium")
    return (Path.home() if home is None else home) / ".atrium"

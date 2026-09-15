"""Read ``atrium.path`` from an instance, resolved against the file that set it."""

from pathlib import Path

from atrium.state.declared_atrium_path import declared_atrium_path

# The schema default (brain/schema/syntopica-config.schema.json, `atrium.path`).
DEFAULT_ATRIUM_PATH = "atrium"


def read_atrium_path(data: Path) -> Path:
    """Return the instance's Atrium state directory.

    ``syntopica.local.json`` outranks ``syntopica.config.json``, and a relative
    value resolves against the file that declared it, which is what lets an
    untracked local file hold an absolute path beside a tracked relative one.
    """
    for name in ("syntopica.local.json", "syntopica.config.json"):
        file = data / name
        value = declared_atrium_path(file)
        if value is not None:
            return (file.parent / value).resolve()
    return (data / DEFAULT_ATRIUM_PATH).resolve()

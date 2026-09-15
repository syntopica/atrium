"""Read ``<section>.path`` from an instance, resolved against the file that set it."""

from pathlib import Path

from atrium.state.declared_section_path import declared_section_path


def read_section_path(data: Path, section: str, default: str) -> Path:
    """Return the directory an instance section points at.

    ``syntopica.local.json`` outranks ``syntopica.config.json``, and a relative
    value resolves against the file that declared it, which is what lets an
    untracked local file hold an absolute path beside a tracked relative one.
    ``default`` is the schema default, relative to the data directory.
    """
    for name in ("syntopica.local.json", "syntopica.config.json"):
        file = data / name
        value = declared_section_path(file, section)
        if value is not None:
            return (file.parent / value).resolve()
    return (data / default).resolve()

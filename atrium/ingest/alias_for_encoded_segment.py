"""The alias a scratchpad's encoded path names, when its directory is gone."""

import re
from collections.abc import Iterable
from pathlib import Path

_HOME = "[HOME]"
# The scratchpad encoding: every character that is not a letter or a digit
# becomes a hyphen (see `decode_workspace_segment`).
_SEPARATOR = re.compile(r"[^A-Za-z0-9]")


def alias_for_encoded_segment(segment: str, home: str | Path, names: Iterable[str]) -> str | None:
    """Return the one alias name whose directory encodes to exactly ``segment``.

    A scratchpad is decoded by walking the real tree, so a project deleted from
    disk cannot be decoded and its sessions lost their workspace: 45
    conversations measured on 2026-09-01. Its old name may still be in the alias
    map, though, and an alias name is a path that can be encoded the same way
    and compared. Only an exact match counts: the encoding turns separators into
    the same hyphen a name contains, so a prefix match would file `p/mem-old`
    under `p/mem`. Two names encoding alike are ambiguous and answer None.
    """
    root = _SEPARATOR.sub("-", str(Path(home).expanduser()))
    found = [
        name
        for name in names
        if name.startswith(_HOME + "/")
        and root + _SEPARATOR.sub("-", name[len(_HOME) :]) == segment
    ]
    return found[0] if len(found) == 1 else None

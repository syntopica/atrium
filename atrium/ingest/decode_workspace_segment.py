"""Recover the real directory an encoded workspace segment stands for."""

import re
from pathlib import Path

# The segment is an absolute path with every character that is not a letter or
# a digit replaced by a hyphen, so `/Users/me/p/inbox-companion` and
# `/Users/me/p/inbox/companion` encode identically, and
# `/Users/me/p/arcade/.worktrees` encodes to `-Users-me-p-arcade--worktrees`.
# The encoding is lossy in exactly the character that separates components, so
# decoding is a search of the real tree rather than a substitution -- splitting
# on hyphens would invent `[HOME]/p/inbox/companion`, a phantom project of the
# same kind this exists to remove.
_SEPARATOR = re.compile(r"[^A-Za-z0-9]")


def decode_workspace_segment(segment: str, home: str | Path) -> str | None:
    """Return the directory ``segment`` encodes, or None when it is unrecoverable.

    Only paths under ``home`` are resolved. A session run in `/private/tmp` or
    at the filesystem root encodes just as faithfully, but neither is a project
    and giving one a workspace would put back the phantom this removes -- so
    anything outside the home directory is dropped rather than decoded.

    When more than one real directory encodes to the same segment the answer is
    None as well. Preferring one of them would file a session run in
    `p/inbox/companion` under `p/inbox-companion`: one project's conversations
    entering another project's memory, which is worse than the phantom, and
    invisible once it happens.

    The prefix test below compares encoded strings, where the separator is the
    same hyphen that appears inside names, so `<home>-old/p/vexa` encodes
    exactly as `<home>/old/p/vexa` does. That ambiguity is not resolvable here
    and no post-check removes it: `_descend` walks only real children of
    ``root``, so its result is under ``root`` by construction and re-encodes to
    the whole segment by construction too. A `resolve()`-based guard is worse
    than none -- it drops a project directory that is a symlink to another
    volume, which is a correct decode.
    """
    root = Path(home).expanduser()
    encoded_root = _SEPARATOR.sub("-", str(root))
    if segment == encoded_root:
        return str(root)
    if not segment.startswith(encoded_root + "-"):
        return None
    found = _descend(root, segment[len(encoded_root) + 1 :])
    if len(found) != 1:
        return None
    return found[0]


def _descend(base: Path, encoded: str) -> list[str]:
    """Walk ``encoded`` down the real tree, returning every directory it can name.

    Every branch is followed rather than the longest one only: a branch that
    consumes the segment but leaves no directory behind is abandoned, and when
    two survive the segment is ambiguous and the caller must not choose.
    """
    if not encoded:
        return [str(base)]
    try:
        entries = [entry for entry in base.iterdir() if entry.is_dir()]
    except OSError:
        return []
    found: list[str] = []
    for entry in entries:
        name = _SEPARATOR.sub("-", entry.name)
        if encoded == name:
            found.append(str(entry))
        elif encoded.startswith(name + "-"):
            found.extend(_descend(entry, encoded[len(name) + 1 :]))
    return found

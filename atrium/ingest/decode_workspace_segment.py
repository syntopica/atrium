"""Recover the real directory an encoded workspace segment stands for."""

import re
from pathlib import Path

from atrium.ingest.descend_encoded_segment import descend_encoded_segment

# The segment is an absolute path with every character that is not a letter or
# a digit replaced by a hyphen, so `/Users/me/p/inbox-tool` and
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
    `p/inbox/companion` under `p/inbox-tool`: one project's conversations
    entering another project's memory, which is worse than the phantom, and
    invisible once it happens.

    The prefix test below compares encoded strings, where the separator is the
    same hyphen that appears inside names, so `<home>-old/p/project-after` encodes
    exactly as `<home>/old/p/project-after` does. That ambiguity is not resolvable here
    and no post-check removes it: `descend_encoded_segment` walks only real children of
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
    found = descend_encoded_segment(root, segment[len(encoded_root) + 1 :])
    if len(found) != 1:
        return None
    return found[0]

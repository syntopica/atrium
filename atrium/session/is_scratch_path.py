"""Whether a path is a scratch location no session record may come from."""

from pathlib import PurePath

# Encoded roots as Claude Code writes them under `~/.claude/projects/`; the
# same three that fed memstore its own curation calls back as conversations
# (771 drawers pruned 2026-08-05).
_ENCODED_PREFIXES = ("-private-tmp", "-tmp", "-var-folders")
_ROOTS = ("/private/tmp", "/tmp", "/private/var/folders", "/var/folders")  # noqa: S108


def is_scratch_path(path: str, tmpdir: str | None = None) -> bool:
    """True for a cwd or transcript under a temporary root."""
    if not path:
        return False
    parts = PurePath(path).parts
    if any(part.startswith(_ENCODED_PREFIXES) for part in parts):
        return True
    roots = [*_ROOTS, *([tmpdir.rstrip("/")] if tmpdir else [])]
    return any(path == root or path.startswith(root + "/") for root in roots)

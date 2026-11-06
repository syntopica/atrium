"""Resolve markdown and wiki links to safe indexed note identifiers."""

import posixpath
import re
from itertools import islice
from pathlib import PurePosixPath
from urllib.parse import unquote

from atrium.context.note_path import note_path


def link_targets(text: str, origin: str) -> list[tuple[str, ...]]:
    """Return bounded relative/root candidate paths, with empty tuples for unsafe links."""
    targets: list[tuple[str, ...]] = []
    pattern = r"\[\[([^\]\n]+)\]\](?!\()|(?<!!)\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+[^)]*)?\)"
    for match in islice(re.finditer(pattern, text), 50):
        target = unquote((match.group(1) or match.group(2)).split("|", 1)[0].split("#", 1)[0])
        if not target:
            continue
        if ":" in target or "\\" in target or target.startswith("/") or "\x00" in target:
            targets.append(())
            continue
        if not PurePosixPath(target).suffix:
            target += ".md"
        relative = note_path(posixpath.normpath(str(PurePosixPath(origin).parent / target)))
        root = note_path(posixpath.normpath(target))
        # A wiki inside the instance (`brain/`) writes `[[topics/x]]` from its
        # own root, so try the note's top directory as well.
        parts = PurePosixPath(origin).parts
        tree = note_path(posixpath.normpath(f"{parts[0]}/{target}")) if len(parts) > 1 else None
        targets.append(tuple(dict.fromkeys(path for path in (relative, root, tree) if path)))
    return targets

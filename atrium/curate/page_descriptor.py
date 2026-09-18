"""The one line a model needs to recognise a curated page: its title and summary."""

from pathlib import Path

_SEPARATOR = "---"
_SUMMARY_LIMIT = 220
# A frontmatter block splits the file into prologue, block and body.
_WITH_FRONTMATTER = 2


def page_descriptor(root: Path, path: str) -> str:
    """Return ``title -- summary`` for a page, or its path when it has neither.

    Frontmatter is read directly rather than parsed with a YAML library: the
    two fields wanted here are scalars, the summary is routinely a folded
    multi-line scalar, and a dependency for that is not worth the audit.
    """
    file = root / path
    if not file.is_file():
        return path
    parts = file.read_text(encoding="utf-8").split(_SEPARATOR)
    block = parts[1] if len(parts) > _WITH_FRONTMATTER else ""
    title = path
    summary = ""
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip("'\"")
        if line.startswith("summary:"):
            rest = [line.split(":", 1)[1]]
            for following in lines[index + 1 :]:
                if following[:1].isalpha():
                    break
                rest.append(following)
            summary = " ".join(" ".join(rest).split()).strip("'\"")[:_SUMMARY_LIMIT]
    return f"{title} -- {summary}" if summary else title

"""Read a ``retired:`` frontmatter block out of one note chunk."""

import re

from atrium.context.retirement import Retirement

# The block as brain's SCHEMA.md documents it: indented `since`, `replaced_by`
# and `terms` (a bracketed, comma-separated list) keys under a `retired:` line.
_BLOCK = re.compile(r"^retired:[ \t]*\n((?:[ \t]+[a-z_]+:.*\n?)+)", re.MULTILINE)
_FIELD = re.compile(r"^[ \t]+([a-z_]+):[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_retirement(text: str, note: str) -> Retirement | None:
    """Return the declared retirement, or None when the block is absent or incomplete."""
    block = _BLOCK.search(text)
    if block is None:
        return None
    fields = {key: value.strip("'\"") for key, value in _FIELD.findall(block.group(1))}
    terms = tuple(
        term.strip().strip("'\"")
        for term in fields.get("terms", "").strip("[]").split(",")
        if term.strip().strip("'\"")
    )
    since = fields.get("since", "")
    if not terms or not _DATE.fullmatch(since):
        return None
    return Retirement(terms, since, fields.get("replaced_by", ""), note)

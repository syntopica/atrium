"""A note's title, taken from its first heading."""


def first_heading(text: str) -> str | None:
    """Return the text of the first Markdown heading, or ``None`` when there is none."""
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None

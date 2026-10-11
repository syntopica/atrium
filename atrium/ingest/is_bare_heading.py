"""Whether a chunk is a Markdown heading and nothing else."""


def is_bare_heading(text: str) -> bool:
    """True for a single heading line with no body beneath it."""
    return "\n" not in text and text.startswith("#")

"""Shorten a text to its head and tail around a visible marker."""


def head_and_tail(text: str, cap: int) -> str:
    """Return ``text`` unchanged when it fits ``cap``, else its two halves and a marker."""
    if len(text) <= cap:
        return text
    half = cap // 2
    return f"{text[:half]}\n[... truncated for synthesis ...]\n{text[-half:]}"

"""Cut a query to a token budget so a query-text pair always fits the model."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tokenizers import Tokenizer


def cap_query_tokens(tokenizer: "Tokenizer", query: str, max_tokens: int) -> str:
    """Return ``query`` unchanged, or its head ending on token ``max_tokens``.

    Pairs are truncated on the text side only, which raises a bare
    ``Exception`` once the query alone fills the model's length; a hook that
    sends a whole prompt as the query hit that on every request. Slicing the
    string by token offsets keeps the head verbatim, with no decode artifacts.
    """
    offsets = tokenizer.encode(query, add_special_tokens=False).offsets
    if len(offsets) <= max_tokens:
        return query
    return query[: offsets[max_tokens - 1][1]]

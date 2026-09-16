"""Split a query into the quoted FTS5 terms every word-lane expression is built from."""

import re


def query_terms(query: str) -> list[str]:
    """Return one quoted FTS5 term per word of ``query``, phrases kept adjacent.

    The index tokenizer splits on punctuation, so `3.7.0` is stored as the three
    adjacent tokens `3 7 0`. Dropping the punctuated term -- or worse, dropping
    every fragment shorter than two characters -- makes a version search return
    nothing at all, in the one lane whose entire purpose is exact recall of
    versions, identifiers and names.

    So a term whose parts were joined by punctuation becomes a PHRASE, which
    matches only where those tokens are adjacent in that order. `3.7.0` finds
    `3.7.0` and not a document that merely mentions 3, 7 and 0 apart.

    Everything is quoted, so a query like `mempalace_delete_drawers()` is a
    search rather than an FTS5 syntax error.
    """
    terms = []
    for raw_term in query.split():
        parts = re.findall(r"[^\W_]+", raw_term, flags=re.UNICODE)
        if not parts:
            continue
        if len(parts) > 1:
            terms.append('"' + " ".join(parts) + '"')
        elif len(parts[0]) > 1 or len(raw_term) > len(parts[0]):
            # A one-character part is kept only when punctuation was stripped
            # from around it, which is what distinguishes `C#` from a stray `a`.
            terms.append(f'"{parts[0]}"')
    return terms

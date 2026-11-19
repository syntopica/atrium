"""Split a query into the quoted FTS5 terms every word-lane expression is built from."""

import re

# A whole prompt sent as the query is not a keyword search. Every term costs the
# broad pass one frequency lookup (~2 ms) outside any budget: a real 33,745-char
# prompt, 4,855 terms, held the auto lane for 24 s against a 7 s client
# (2026-11-19). 128 terms keep a pass near 0.3 s and cover ~850 chars of prose.
# shortcut: only the head of the prompt is weighed, and the broad pass keeps its
# rarest terms; weigh more of it when a long query's tail is shown to carry the
# match.
_MAX_TERMS = 128


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

    Everything is quoted, so a query like `memstore_delete_drawers()` is a
    search rather than an FTS5 syntax error.

    A repeated term is returned once, and only the first ``_MAX_TERMS`` distinct
    terms are kept.
    """
    terms: dict[str, None] = {}
    for raw_term in query.split():
        if len(terms) == _MAX_TERMS:
            break
        parts = re.findall(r"[^\W_]+", raw_term, flags=re.UNICODE)
        if not parts:
            continue
        if len(parts) > 1:
            terms['"' + " ".join(parts) + '"'] = None
        elif len(parts[0]) > 1 or len(raw_term) > len(parts[0]):
            # A one-character part is kept only when punctuation was stripped
            # from around it, which is what distinguishes `C#` from a stray `a`.
            terms[f'"{parts[0]}"'] = None
    return list(terms)

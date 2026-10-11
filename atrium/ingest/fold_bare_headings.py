"""Attach heading-only sections to the content they introduce."""

from atrium.ingest.is_bare_heading import is_bare_heading


def fold_bare_headings(sections: list[str]) -> list[str]:
    """Prefix each heading-only section onto the section after it.

    A lone heading carries no answer, yet as its own chunk it earned a vector
    and outranked real content in dense queries. A trailing one introduces
    nothing and is dropped, unless it is all the note holds.
    """
    folded: list[str] = []
    pending = ""
    for section in sections:
        merged = f"{pending}\n\n{section}" if pending else section
        if is_bare_heading(section):
            pending = merged
            continue
        folded.append(merged)
        pending = ""
    if pending and not folded:
        folded.append(pending)
    return folded

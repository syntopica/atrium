"""Interleave history, notes and each note's links into one candidate order."""

from atrium.retrieve.hit import Hit


def interleave_candidates(
    history: list[Hit], notes: list[Hit], links: list[tuple[Hit, str]]
) -> list[tuple[Hit, str, str | None]]:
    """Alternate one history hit and one note, each note followed by its links."""
    candidates: list[tuple[Hit, str, str | None]] = []
    for position in range(max(len(history), len(notes), len(links))):
        if position < len(history):
            candidates.append((history[position], "history", None))
        if position < len(notes):
            candidates.append((notes[position], "curated", None))
            candidates.extend(
                (hit, "link", parent)
                for hit, parent in links
                if parent == notes[position].record_id
            )
    return candidates

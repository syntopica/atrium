"""A tool, service or practice the owner declared retired, and what replaced it."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Retirement:
    """One ``retired:`` block, read from the frontmatter of the note declaring it.

    ``since`` is an ISO date. History authored before it describes the retired
    thing as current, which is how an agent kept reaching for Holded weeks after
    invoicing had moved to InteliFactu.
    """

    terms: tuple[str, ...]
    since: str
    replaced_by: str
    note: str

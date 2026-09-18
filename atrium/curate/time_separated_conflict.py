"""Demote a conflict between two claims that were never seen at the same time."""


def time_separated_conflict(
    left_first: str, left_last: str, right_first: str, right_last: str
) -> bool:
    """Return whether the two sighting windows do not overlap.

    A conflict between claims sighted in disjoint windows is almost never a
    contradiction: it is the same thing measured twice, or renamed, or grown.
    Measured on the 8 pairs the first run called conflicting: 7 were the same
    measurement taken on different days, and the eighth was an application
    renamed between July and August, which is supersession rather than
    disagreement.

    Dates are deliberately kept OUT of the pair prompt itself. Prefixing the
    statements with their sighting dates does fix the contradictions - 8 down
    to 1 - but it costs every merge: all four pairs the run had called
    `equivalent` came back `unrelated` or `complementary`, because the model
    reads two dates as two subjects.
    """
    return left_last < right_first or right_last < left_first

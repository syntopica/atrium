"""The `status --coverage` report printer."""

from typing import Any


def print_coverage(coverage: dict[str, Any]) -> None:
    """Report coverage over real projects, not over every directory ever opened.

    Counting every workspace makes coverage read 2.1% while the work that
    matters is above half. The alarming number and the useful one are different
    numbers; this prints the useful one, and names the projects a recall would
    answer nothing for.
    """
    share = 100 * coverage["covered"] / coverage["projects"] if coverage["projects"] else 0.0
    print(
        f"  project coverage: {coverage['covered']} of {coverage['projects']} projects "
        f"with >={coverage['floor']} conversations have memory ({share:.0f}%)"
    )
    for workspace, conversations in coverage["uncovered"]:
        print(f"    no memory: {workspace:<40} {conversations:>6,} conversations")

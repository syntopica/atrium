"""Fold a renamed project onto the name it has now."""


def apply_workspace_aliases(workspace: str, aliases: dict[str, str]) -> str:
    """Return ``workspace`` under its current name, subdirectories included.

    A rename splits memory the same way a missed redaction does, and more
    quietly: `p/provertly` runs to 2026-07-10 and `p/verticagtm` starts
    2026-07-12, so the project's first month answered nothing from inside the
    project.

    Longest alias first, so a nested rename cannot be shadowed by a shorter one
    that also matches, and the boundary is a path separator, so
    `p/provertly-archive` is its own project rather than part of the rename.
    """
    for old in sorted(aliases, key=len, reverse=True):
        root = old.rstrip("/")
        if workspace == root:
            return aliases[old]
        if workspace.startswith(root + "/"):
            return aliases[old].rstrip("/") + workspace[len(root) :]
    return workspace

"""Fold a renamed project onto the name it has now."""

from collections.abc import Mapping

from atrium.ingest.workspace_alias import WorkspaceAlias


def apply_workspace_aliases(
    workspace: str,
    aliases: Mapping[str, str | WorkspaceAlias],
    started_at: str | None = None,
) -> str:
    """Return ``workspace`` under its current name, subdirectories included.

    A rename splits memory the same way a missed redaction does, and more
    quietly: `p/project-before` runs to 2026-07-10 and `p/project-after` starts
    2026-07-12, so the project's first month answered nothing from inside the
    project.

    Longest alias first, so a nested rename cannot be shadowed by a shorter one
    that also matches, and the boundary is a path separator, so
    `p/project-before-archive` is its own project rather than part of the rename.

    A dated alias applies only to conversations started before its ``until``;
    with no start date known it applies, as an undated one does.
    """
    for old in sorted(aliases, key=len, reverse=True):
        alias = aliases[old]
        if isinstance(alias, str):
            alias = WorkspaceAlias(alias)
        if alias.until and started_at and started_at[:10] >= alias.until:
            continue
        root = old.rstrip("/")
        if workspace == root:
            return alias.to
        if workspace.startswith(root + "/"):
            return alias.to.rstrip("/") + workspace[len(root) :]
    return workspace

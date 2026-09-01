"""One spelling per project, so a project's memory is not split in two."""

from pathlib import Path

from atrium.ingest.apply_workspace_aliases import apply_workspace_aliases

# The exporter redacts the user's home directory to this before archiving, and
# `project_workspace` resolves a live cwd to the same form. Anything still
# carrying a real home path is a redaction the exporter missed.
_HOME = "[HOME]"


def canonical_workspace(
    workspace: str | None,
    home: str | Path | None = None,
    aliases: dict[str, str] | None = None,
) -> str | None:
    """Return ``workspace`` in the one spelling this project answers to.

    Two things split a project's memory, and both are folded here: a home
    directory the exporter failed to redact, and a rename. ``aliases`` maps an
    old workspace to the current one.

    Measured 2026-09-01: 29 projects were present in the index under *both*
    spellings, and 4,053 conversations sat under the unredacted one. Since
    project-scoped recall and `--project` search both ask for the `[HOME]`
    form, that half of each project was invisible to them -- 1,331 of
    intelifactu's conversations, a third of it, unreachable from inside the
    project itself.

    Normalizing here rather than at query time keeps one spelling in the index,
    which is also the only place it can be fixed cheaply: the archive is
    canonical and must not be rewritten, while the index is derived and rebuilt
    from it. It removes a leak too -- the real username had no business being
    stored in a field the redaction was meant to clear.
    """
    if not workspace:
        return workspace
    root = str(Path(home).expanduser() if home is not None else Path.home())
    if workspace == root:
        return _HOME
    prefix = root.rstrip("/") + "/"
    if workspace.startswith(prefix):
        workspace = _HOME + "/" + workspace[len(prefix) :]
    return apply_workspace_aliases(workspace, aliases or {})

"""One spelling per project, so a project's memory is not split in two."""

from collections.abc import Mapping
from pathlib import Path

from atrium.ingest.apply_workspace_aliases import apply_workspace_aliases
from atrium.ingest.decode_workspace_segment import decode_workspace_segment
from atrium.ingest.session_scratchpad_segment import session_scratchpad_segment
from atrium.ingest.workspace_alias import WorkspaceAlias

# The exporter redacts the user's home directory to this before archiving, and
# `project_workspace` resolves a live cwd to the same form. Anything still
# carrying a real home path is a redaction the exporter missed.
_HOME = "[HOME]"


def canonical_workspace(
    workspace: str | None,
    home: str | Path | None = None,
    aliases: Mapping[str, str | WorkspaceAlias] | None = None,
    started_at: str | None = None,
) -> str | None:
    """Return ``workspace`` in the one spelling this project answers to.

    Three things keep a project's memory from answering, and all are folded
    here: a home directory the exporter failed to redact, a rename, and a
    per-session scratchpad standing in for the project it was working on.
    ``aliases`` maps an old workspace to the current one; a dated alias is
    skipped for a conversation whose ``started_at`` is on or after its date.

    Measured 2026-09-01: 29 projects were present in the index under *both*
    spellings, and 4,053 conversations sat under the unredacted one. Since
    project-scoped recall and `--project` search both ask for the `[HOME]`
    form, that half of each project was invisible to them -- 1,331 of
    wide-project's conversations, a third of it, unreachable from inside the
    project itself.

    A scratchpad returns None when its encoded path names nothing under the
    home directory: an unrecoverable one is a temporary directory and no
    project, and stamping it on a record would leave the phantom project this
    removes. None here is the same absence as a conversation that never had a
    workspace -- the records are kept, unattached to any project.

    Normalizing here rather than at query time keeps one spelling in the index,
    which is also the only place it can be fixed cheaply: the archive is
    canonical and must not be rewritten, while the index is derived and rebuilt
    from it. It removes a leak too -- the real username had no business being
    stored in a field the redaction was meant to clear.

    The scratchpad decode is the one part of this that reads the live
    filesystem, so ingest is no longer a pure function of the archive: the same
    archive yields different workspaces on a machine where a project directory
    is absent, and a project deleted tomorrow loses its scratchpad history on
    the next refresh rather than keeping the workspace it had. That is the
    mechanism behind the 45 conversations dropped in the 2026-09-01 measurement,
    and it means "the index is derived and rebuilt from the archive" now holds
    only up to the state of the disk at rebuild time.
    """
    if not workspace:
        return workspace
    root = str(Path(home).expanduser() if home is not None else Path.home())
    segment = session_scratchpad_segment(workspace)
    if segment is not None:
        decoded = decode_workspace_segment(segment, root)
        if decoded is None:
            return None
        workspace = decoded
    if workspace == root:
        return _HOME
    prefix = root.rstrip("/") + "/"
    if workspace.startswith(prefix):
        workspace = _HOME + "/" + workspace[len(prefix) :]
    return apply_workspace_aliases(workspace, aliases or {}, started_at)

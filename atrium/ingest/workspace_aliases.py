"""Old project names, folded onto the name the project has now."""

import json
from pathlib import Path

from atrium.ingest.workspace_alias import WorkspaceAlias
from atrium.state.state_directory import state_directory

# Small, hand-maintained, and deliberately not derivable: only a person knows
# that `p/consumer-pv` became `p/consumer-g` rather than being deleted while an
# unrelated project appeared. Kept beside the index rather than inside it
# because a rebuild must not lose it -- it is a few lines a human wrote, so the
# right place for the copy of record is the operator's dotfiles.
ALIASES_NAME = "workspace-aliases.json"


def workspace_aliases(path: Path | None = None) -> dict[str, WorkspaceAlias]:
    """Return {old workspace: alias}, empty when there is no file.

    An entry is either the current name, or ``{"to": name, "until": date}``
    when the old directory was reused after that date.

    Without a path the file is looked for in the state directory of the
    instance selected by the environment and working directory.

    A rename splits a project's memory in two exactly as a missed redaction
    does, and more quietly: `p/consumer-pv` holds 558 conversations from
    2026-06-14 to 2026-07-10 and `p/consumer-g` picks up on 2026-07-12, so a
    session in the project today recalls nothing from its first month.

    An unreadable or malformed file returns no aliases rather than raising: the
    aliases are a refinement, and ingest must not stop because a hand-edited
    JSON file has a trailing comma.
    """
    if path is None:
        path = state_directory() / ALIASES_NAME
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    aliases = {}
    for old, new in loaded.items():
        if not old or not new:
            continue
        if isinstance(new, dict):
            if not new.get("to"):
                continue
            aliases[str(old)] = WorkspaceAlias(str(new["to"]), new.get("until") or None)
        else:
            aliases[str(old)] = WorkspaceAlias(str(new))
    return aliases

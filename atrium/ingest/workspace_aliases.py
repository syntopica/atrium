"""Old project names, folded onto the name the project has now."""

import json
from pathlib import Path

# Small, hand-maintained, and deliberately not derivable: only a person knows
# that `p/consumer-pv` became `p/consumer-g` rather than being deleted while an
# unrelated project appeared. Kept beside the index rather than inside it
# because a rebuild must not lose it -- it is a few lines a human wrote, so the
# right place for the copy of record is the operator's dotfiles.
DEFAULT_ALIASES = Path.home() / ".atrium" / "workspace-aliases.json"


def workspace_aliases(path: Path = DEFAULT_ALIASES) -> dict[str, str]:
    """Return {old workspace: current workspace}, empty when there is no file.

    A rename splits a project's memory in two exactly as a missed redaction
    does, and more quietly: `p/consumer-pv` holds 558 conversations from
    2026-06-14 to 2026-07-10 and `p/consumer-g` picks up on 2026-07-12, so a
    session in the project today recalls nothing from its first month.

    An unreadable or malformed file returns no aliases rather than raising: the
    aliases are a refinement, and ingest must not stop because a hand-edited
    JSON file has a trailing comma.
    """
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {str(old): str(new) for old, new in loaded.items() if old and new}

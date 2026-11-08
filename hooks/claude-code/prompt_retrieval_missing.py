"""Print the Claude Code settings file that lacks per-prompt retrieval, if any.

The session-start hook runs this so a profile whose settings lost the
atrium-context plugin says so in every session, rather than only in an
`atrium doctor` run nobody reads: a settings sync dropped the plugin on
2026-10-18 and again on 2026-11-07, and both times sessions silently stopped
retrieving per prompt. Uses the doctor's own predicate, imported from the
checkout this file lives in, so the two never disagree. Prints nothing when the
profile retrieves, or when its settings cannot be read.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from atrium.doctor.has_prompt_retrieval import has_prompt_retrieval

profile = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
settings = profile / "settings.json"
try:
    document = json.loads(settings.read_text())
except (OSError, json.JSONDecodeError):
    sys.exit(0)
if not has_prompt_retrieval(document):
    print(settings)

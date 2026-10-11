#!/bin/sh
# Codex PostToolUse and Stop hook: the turn's brain use as one line at its end.
# See brain_use.py. Register both events to this script,
# with SYNTOPICA_DATA set so a note opened from the shell is recognised:
#   {"type": "command", "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/codex/brain-use.sh", "timeout": 10}
python3 "$(dirname "$0")/brain_use.py" 2>/dev/null || true
exit 0

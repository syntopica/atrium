#!/bin/sh
# Claude Code Stop hook: the session records its own episode.
#
# Everything is decided by `atrium session-stop` (docs/designs/session-producer.md):
# this file only finds the command. No daemon, no queue, no state outside the
# instance; when atrium is not installed the hook is silent and the session
# loses the feature, never a turn. Register under "Stop" in ~/.claude/settings.json:
#   {"type": "command", "command": "sh /path/to/hooks/claude-code/stop-record-episode.sh", "timeout": 30}
if command -v atrium >/dev/null 2>&1; then
  exec atrium session-stop
fi
if [ -n "${ATRIUM_CHECKOUT:-}" ] && [ -f "$ATRIUM_CHECKOUT/pyproject.toml" ]; then
  cd "$ATRIUM_CHECKOUT" && exec uv run --quiet atrium session-stop
fi
cat >/dev/null
exit 0

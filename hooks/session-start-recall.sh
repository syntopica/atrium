#!/usr/bin/env bash
# SessionStart recall: inject what Atrium already knows about this project.
#
# Claude Code and Codex read the same SessionStart contract: `additionalContext`
# under `hookSpecificOutput` for the model, `systemMessage` for the person, and
# `cwd` on stdin. Register it in either, on every source (startup, resume,
# clear, compact), so a compacted or cleared session is recalled again:
#   {"type": "command", "command": "bash /path/to/atrium/hooks/session-start-recall.sh", "timeout": 25}
#
# Replaces the mempalace recall hook. That one injected literal message tails
# filed as CHECKPOINT drawers -- a wall of near-duplicate lines with no content.
# This injects synthesized episode titles, which is the thing sessions actually
# needed from it.
#
# Deliberate divergence from the frozen-snapshot design in atrium's TODO: that
# discipline exists to keep the injected prefix stable and cheap, and `atrium
# recall` is already deterministic given the index and runs in ~1.2s with no
# embedder. A snapshot file would add a staleness window and a writer for no
# measured gain. Revisit if recall ever needs the dense lane.
set -uo pipefail

# The CLI on PATH, not `uv run` from a checkout: the wrapper pins the instance
# and answers in ~0.1s warm, where a cold `uv run` re-resolves dependencies and
# has been measured at ~20s -- against this hook's 25s timeout. The checkout
# holding this script is only the fallback.
ATRIUM_CHECKOUT="$(cd "$(dirname "$0")/.." && pwd)"
command -v atrium >/dev/null 2>&1 || [ -d "$ATRIUM_CHECKOUT" ] || exit 0

input=$(cat 2>/dev/null || true)

cwd=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('cwd', ''))
except Exception:
    print('')
" 2>/dev/null)
[ -z "$cwd" ] && cwd="$PWD"

errors=$(mktemp)
if command -v atrium >/dev/null 2>&1; then
  out=$(timeout 20 atrium recall --cwd "$cwd" 2>"$errors")
else
  out=$(cd "$ATRIUM_CHECKOUT" && timeout 20 uv run atrium recall --cwd "$cwd" 2>"$errors")
fi
status=$?
reason=$(tail -3 "$errors")
rm -f "$errors"

if [ "$status" -ne 0 ]; then
  # Recall broke. Say so: an agent told nothing is known about this project
  # will confidently re-derive what is already in the index, and neither it nor
  # the user has any way to tell that apart from a project with no history.
  [ "$status" -eq 124 ] && reason="atrium recall timed out after 20s"
  out="# atrium recall unavailable

Memory could not be read for this session, so an empty recall means nothing.
Do not treat this project as having no history.

    ${reason:-atrium recall exited $status}"
elif [ -z "$out" ]; then
  # Genuinely nothing to recall. Inject nothing rather than spend context
  # saying so.
  exit 0
fi

# additionalContext never reaches the transcript, so the person could not tell
# a recall from a silence. systemMessage is the one line they see.
if [ "$status" -ne 0 ]; then
  notice="atrium: recall unavailable (${reason:-exit $status})"
else
  notice="atrium: $(printf '%s\n' "$out" | grep -c '^- ') episodes recalled for this project"
fi

printf '%s' "$out" | NOTICE="$notice" python3 -c "
import json, os, sys
print(json.dumps({
    'systemMessage': os.environ['NOTICE'].splitlines()[0][:200],
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': sys.stdin.read().strip(),
    }
}))
" 2>/dev/null || true
exit 0

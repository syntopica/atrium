#!/bin/sh
# Claude Code UserPromptSubmit hook: retrieve before the session answers.
#
# The session-start recall block lists what a project already knows, but a list
# of titles is only a prompt to go and ask, and sessions largely did not ask:
# unless the person wrote "search atrium" by hand, obvious ground already in the
# index was re-derived from scratch. This hook does the asking, per prompt, so
# the evidence is in front of the model at the moment the question is posed.
#
# The dense lane, not the lexical one, and that is measured rather than a taste:
# a prompt is a natural-language sentence, and on a 1.4M-record index the word
# lane ORs every common term in it -- "why does the stop hook fire on a status
# turn" took over two minutes, against 1-3s for the same query dense. Plus a
# hard 5s timeout and a small budget. Silence on every failure -- a hook that
# cannot answer must never block a turn; it can still delay one by up to that
# timeout, which is the price of injecting anything at all before the turn
# starts. Register under "UserPromptSubmit":
#   {"type": "command", "command": "sh /path/to/hooks/claude-code/user-prompt-context.sh", "timeout": 15}
#
# Tunable through the environment: ATRIUM_PROMPT_CONTEXT_LIMIT (evidence items),
# ATRIUM_PROMPT_CONTEXT_CHARS (retrieval budget), ATRIUM_PROMPT_CONTEXT_TIMEOUT.
# ATRIUM_PROMPT_CONTEXT_LANE picks the retrieval lane. Set ATRIUM_PROMPT_CONTEXT=off
# to disable without unregistering the hook.
set -u

[ "${ATRIUM_PROMPT_CONTEXT:-on}" = "off" ] && { cat >/dev/null 2>&1; exit 0; }
command -v atrium >/dev/null 2>&1 || { cat >/dev/null 2>&1; exit 0; }

payload=$(cat 2>/dev/null || true)
[ -n "$payload" ] || exit 0

limit="${ATRIUM_PROMPT_CONTEXT_LIMIT:-4}"
chars="${ATRIUM_PROMPT_CONTEXT_CHARS:-1400}"
seconds="${ATRIUM_PROMPT_CONTEXT_TIMEOUT:-5}"

printf '%s' "$payload" | ATRIUM_PROMPT_CONTEXT_LIMIT="$limit" \
  ATRIUM_PROMPT_CONTEXT_CHARS="$chars" ATRIUM_PROMPT_CONTEXT_TIMEOUT="$seconds" \
  ATRIUM_PROMPT_CONTEXT_LANE="${ATRIUM_PROMPT_CONTEXT_LANE:-dense}" \
  python3 "$(dirname "$0")/user_prompt_context.py" 2>/dev/null || true
exit 0

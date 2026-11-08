#!/bin/sh
# Preserve the existing registration while sharing the packaged implementation.
# This entry point is Claude Code's, so it also names a profile that lost the
# atrium-context plugin; the packaged script reports it to the person and the model.
here=$(dirname "$0")
ATRIUM_PROMPT_RETRIEVAL_OFF=$(python3 "$here/claude-code/prompt_retrieval_missing.py" 2>/dev/null)
export ATRIUM_PROMPT_RETRIEVAL_OFF
exec bash "$here/../plugins/atrium-codex/hooks/session-start-recall.sh"

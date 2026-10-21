#!/bin/sh
# Preserve the existing registration while sharing the packaged implementation.
exec sh "$(dirname "$0")/../../plugins/atrium-codex/hooks/subagent-start.sh"

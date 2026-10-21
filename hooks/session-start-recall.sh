#!/bin/sh
# Preserve the existing registration while sharing the packaged implementation.
exec bash "$(dirname "$0")/../plugins/atrium-codex/hooks/session-start-recall.sh"

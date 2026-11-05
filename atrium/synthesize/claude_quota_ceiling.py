"""The share of a subscription window synthesis may spend before it yields."""

# The Claude lane runs on the Favish profile, whose weekly limit is shared with
# Favish work (owner, 2026-11-05). Synthesis is a backlog that can wait for the
# reset; interactive work cannot, so the pass stops with a fifth of the
# fullest window still free. claude-mem pauses its observer the same way.
CLAUDE_QUOTA_CEILING = 0.8

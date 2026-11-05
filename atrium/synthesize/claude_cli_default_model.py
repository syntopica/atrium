"""The model the Claude Code CLI lane runs when none is pinned."""

# Synthesis is extraction from one transcript, so the smallest current model is
# the right price; the lane exists to drain a backlog off the local machines.
CLAUDE_CLI_DEFAULT_MODEL = "claude-haiku-5-5"

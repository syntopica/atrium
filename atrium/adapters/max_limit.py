"""The ceiling on any MCP tool's result count."""

# A limit is a promise about how much context the answer will spend. Left
# unbounded, one tool call can flood the agent that asked; left unchecked, a
# negative one reaches SQLite as "no limit".
MAX_LIMIT = 50

"""A shell command that creates a Git commit, with or without `-C <dir>`."""

import re

GIT_COMMIT_PATTERN = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b")

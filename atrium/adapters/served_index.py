"""The index file the MCP adapter serves."""

import os
from pathlib import Path

from atrium.state.state_directory import state_directory

# Configurable, because this server and the CLI must be able to disagree about
# which index they serve on purpose rather than by accident -- a second index at
# the default path would otherwise be served silently.
INDEX = (
    Path(os.environ["ATRIUM_INDEX"])
    if os.environ.get("ATRIUM_INDEX")
    else state_directory() / "index.sqlite3"
)

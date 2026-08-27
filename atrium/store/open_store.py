"""Open the index database, creating the schema when absent."""

import sqlite3
from pathlib import Path
from urllib.parse import quote

from atrium.store.schema import SCHEMA

# Readers must never block behind the writer. This is the one lesson the previous
# system paid for twice: in rollback-journal mode a search waited on every mine
# and took 2m55s at 4% CPU. WAL is safe here because nothing memory-maps this
# database -- the SIGBUS crashes that forced WAL off there came from chromadb
# holding a stale mmap across a checkpoint, and Atrium holds no such handle.
_PRAGMAS = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA busy_timeout = 30000",
    "PRAGMA foreign_keys = ON",
)


def open_store(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Return a connection to the index at ``path``.

    A read-only connection never creates the schema: if the index is missing, the
    caller asked to read something that has not been built, and inventing an empty
    database would answer their query with a confident "no results".
    """
    if read_only:
        if not path.exists():
            raise FileNotFoundError(f"no index at {path}; run `atrium ingest` first")
        # The path goes into a URI, so `?` and `#` in a filename would be read
        # as the query and fragment separators and silently open the wrong file.
        uri = f"file:{quote(str(path.resolve()))}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    for pragma in _PRAGMAS:
        connection.execute(pragma)
    connection.executescript(SCHEMA)
    return connection

"""The curated layer as one handle: the index that finds pages and the tree holding them."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from atrium.embed.embedder import Embedder


@dataclass(frozen=True)
class PageLibrary:
    """Everything a placement needs about the wiki, passed as one argument."""

    connection: sqlite3.Connection
    embedder: Embedder
    root: Path

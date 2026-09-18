"""Read the curated layer out of the index and prepare it for scoring."""

import re
import sqlite3
from pathlib import Path

import numpy as np

from atrium.curate.page_library import PageLibrary
from atrium.embed.embedder import Embedder
from atrium.retrieve.fold import fold

_QUERY = """
SELECT r.conversation_id, r.title, r.text, v.vector
FROM records r
LEFT JOIN vectors v ON v.record_id = r.record_id
WHERE r.provider = 'brain'
ORDER BY r.record_id
"""
_WORD = re.compile(r"[a-z0-9_]+")


def load_page_library(
    connection: sqlite3.Connection, embedder: Embedder, root: Path
) -> PageLibrary:
    """Return the curated chunks, tokenised and stacked, for one proposal run."""
    rows = connection.execute(_QUERY).fetchall()
    texts = [str(row[2]) for row in rows]
    embedded = [index for index, row in enumerate(rows) if row[3] is not None]
    matrix = (
        np.frombuffer(b"".join(rows[index][3] for index in embedded), dtype=np.float32).reshape(
            len(embedded), -1
        )
        if embedded
        else np.zeros((0, 1), dtype=np.float32)
    )
    return PageLibrary(
        paths=[str(row[0]) for row in rows],
        titles=[str(row[1]) for row in rows],
        texts=texts,
        words=[set(_WORD.findall(fold(text).lower())) for text in texts],
        matrix=matrix,
        embedded=embedded,
        embedder=embedder,
        root=root,
    )

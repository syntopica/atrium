"""The curated layer loaded once: its chunks, their words and their vectors."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from atrium.embed.embedder import Embedder


@dataclass(frozen=True)
class PageLibrary:
    """Everything a placement needs about the wiki, prepared once per run.

    Both lanes run over these arrays rather than over SQL. Re-deriving them per
    claim is what made the first version unusable: tokenising 4,889 chunks and
    scoring bm25 across the whole index cost 29 s a claim.
    """

    paths: list[str]
    titles: list[str]
    texts: list[str]
    words: list[set[str]]
    matrix: np.ndarray
    embedded: list[int]
    embedder: Embedder
    root: Path

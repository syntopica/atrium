"""Embed a whole candidate ledger to a memory-mapped matrix, resumably."""

import json
import time
from pathlib import Path

import numpy as np

from atrium.context.context_embedder import ContextEmbedder
from atrium.curate.candidate_texts import candidate_texts

_DIM = 384
# One chunk is one flush of the memmap and one progress line. 2,000 texts is
# about 35 s of CPU on this machine, small enough that a killed run loses
# little and large enough that the flushes are not the cost.
_CHUNK = 2_000


def embedded_ledger(
    ledger: Path, matrix_path: Path, ids_path: Path, embedder: ContextEmbedder
) -> tuple[np.memmap, list[str]]:
    """Return the ledger's vectors and ids, embedding whatever is missing.

    The matrix is a memmap rather than an array: 288,844 claims at 384 float32
    dimensions are 444 MB, which fits in memory but not beside a chunked
    similarity scan that wants the rest of it.

    Resumable by row count -- an interrupted run leaves a shorter matrix and
    the ids file says how many rows are trustworthy, so the next run continues
    instead of paying the whole pass again.
    """
    ids = [candidate_id for candidate_id, _ in candidate_texts(ledger)]
    ids_path.write_text("".join(json.dumps(candidate_id) + "\n" for candidate_id in ids))
    done = 0
    if matrix_path.exists():
        done = matrix_path.stat().st_size // (_DIM * 4)
    if done > len(ids):
        raise RuntimeError(
            f"{matrix_path} holds {done} rows for a ledger of {len(ids)}; delete it to re-embed"
        )
    matrix = np.memmap(
        matrix_path, dtype=np.float32, mode="r+" if done else "w+", shape=(len(ids), _DIM)
    )
    if done == len(ids):
        return matrix, ids
    started = time.monotonic()
    texts = [text for _, text in candidate_texts(ledger)]
    for start in range(done, len(ids), _CHUNK):
        chunk = texts[start : start + _CHUNK]
        matrix[start : start + len(chunk)] = embedder.embed(chunk)
        matrix.flush()
        elapsed = time.monotonic() - started
        rate = (start + len(chunk) - done) / max(elapsed, 1e-9)
        remaining = (len(ids) - start - len(chunk)) / max(rate, 1e-9)
        print(
            f"  embedded {start + len(chunk):,}/{len(ids):,}"
            f" at {rate:,.0f}/s, {remaining / 60:,.0f} min left",
            flush=True,
        )
    return matrix, ids

"""Drop rows from a memory-mapped matrix and the id list aligned with it."""

import json
import os
from collections.abc import Collection
from pathlib import Path

import numpy as np

_DIM = 384


def scrub_aligned_matrix(ids_path: Path, matrix_path: Path, drop: Collection[str]) -> int:
    """Remove the rows whose id is in ``drop`` from both files; return rows removed.

    ``candidate-ids.jsonl`` and ``candidates.f32`` are aligned row for row, and
    the embedder resumes by the matrix's row count, so both are rewritten
    together, matrix first. A pair whose row count no longer matches its id list
    -- a run stopped between the two replacements -- is not reconciled but
    dropped: it is a cache, and the embedder resuming over a misaligned pair
    would label vectors with the wrong candidates.
    """
    if not ids_path.is_file() or not matrix_path.is_file():
        # Half a pair cannot be cleaned row by row; it is a cache, so it goes.
        orphan = matrix_path if matrix_path.is_file() else ids_path
        if not orphan.is_file():
            return 0
        rows = matrix_path.stat().st_size // (_DIM * 4) if orphan == matrix_path else 0
        orphan.unlink()
        return rows
    ids = [json.loads(line) for line in ids_path.read_text(encoding="utf-8").splitlines() if line]
    rows = matrix_path.stat().st_size // (_DIM * 4)
    if rows != len(ids):
        matrix_path.unlink()
        ids_path.unlink()
        return rows
    keep = [i for i in range(rows) if ids[i] not in drop]
    if len(keep) == rows:
        return 0
    matrix = np.memmap(matrix_path, dtype=np.float32, mode="r", shape=(rows, _DIM))
    temporary = matrix_path.with_name(f".{matrix_path.name}.tmp-{os.getpid()}")
    np.ascontiguousarray(matrix[keep]).tofile(temporary)
    del matrix
    kept_ids = [ids[i] for i in keep]
    ids_temporary = ids_path.with_name(f".{ids_path.name}.tmp-{os.getpid()}")
    ids_temporary.write_text("".join(json.dumps(i) + "\n" for i in kept_ids), encoding="utf-8")
    temporary.replace(matrix_path)
    ids_temporary.replace(ids_path)
    return rows - len(keep)

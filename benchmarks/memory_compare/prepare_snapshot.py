"""Freeze one shared semantic corpus without consulting answer labels."""

import hashlib
import json
from pathlib import Path

import numpy as np

from atrium.context.build_dense_matrix import build_dense_matrix
from atrium.context.save_dense_matrix import save_dense_matrix
from atrium.session.redact_sensitive_text import redact_sensitive_text
from atrium.sql.load_sql import load_sql
from atrium.store.open_store import open_store


def prepare_snapshot(index: Path, directory: Path) -> dict:
    """Copy the exact embedded records to a new disposable index and JSONL."""
    target = directory / "snapshot.sqlite3"
    if target.exists():
        raise FileExistsError("use a new output directory; snapshots are immutable")
    directory.mkdir(parents=True, exist_ok=True)
    source = open_store(index, read_only=True)
    source.execute(load_sql("context/begin_read"))
    destination = open_store(target)
    digest = hashlib.sha256()
    count = 0
    excluded = 0
    vectors = {}
    with (directory / "corpus.jsonl").open("w") as handle, destination:
        for row in source.execute(load_sql("benchmark/semantic_snapshot")):
            values, vector = row[:-1], row[-1]
            if redact_sensitive_text(values[6]) != values[6]:
                excluded += 1
                continue
            # Exact duplicate text receives the same vector in every backend.
            vector = vectors.setdefault(hashlib.sha256(values[6].encode()).digest(), vector)
            norm = np.linalg.norm(np.frombuffer(vector, dtype=np.float32))
            if not np.isfinite(norm) or abs(norm - 1) > 0.001:  # noqa: PLR2004 -- stored-vector tolerance
                raise ValueError("invalid corpus vector")
            destination.execute(load_sql("store/insert_record"), values)
            destination.execute(
                load_sql("store/insert_vector_guarded"), (vector, values[0], values[3])
            )
            item = dict(
                zip(
                    (
                        "record_id",
                        "event_id",
                        "conversation_id",
                        "source_sha256",
                        "provider",
                        "role",
                        "text",
                        "authored_at",
                        "workspace",
                        "title",
                        "event_index",
                    ),
                    values,
                    strict=True,
                )
            )
            line = json.dumps(item, ensure_ascii=False) + "\n"
            handle.write(line)
            digest.update(line.encode())
            digest.update(vector)
            count += 1
            if count % 1000 == 0:
                print(f"snapshot {count}", flush=True)
        for row in source.execute(load_sql("benchmark/read_supersessions")):
            destination.execute(load_sql("store/insert_supersession"), row)
    save_dense_matrix(build_dense_matrix(destination), directory / "matrix.npz")
    source.close()
    destination.close()
    return {
        "records": count,
        "corpus_vector_sha256": digest.hexdigest(),
        "roles": ["note", "synthesis"],
        "selection": "embedded semantic records unchanged by the current secret redactor",
        "excluded_by_redactor": excluded,
    }

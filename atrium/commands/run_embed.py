"""The `embed` handler of the atrium CLI."""

from pathlib import Path

from atrium.store.open_store import open_store


def run_embed(index: Path) -> int:
    """Embed every semantic-layer record that has no vector yet.

    Vectors commit per batch rather than per run: an interrupted embed keeps
    what it finished (each vector is valid alone), and the next run resumes
    from the missing ones.
    """
    import json
    from functools import partial

    from atrium.embed.embedder import Embedder
    from atrium.embed.model_is_cached import model_is_cached
    from atrium.embed.model_repo import MODEL_REPO
    from atrium.embed.semantic_roles import SEMANTIC_ROLES
    from atrium.sql.load_sql import load_sql
    from atrium.store.commit_with_retry import commit_with_retry
    from atrium.store.write_vectors import write_vectors

    # Every step below can block for minutes without spending any CPU: the open
    # waits on another writer's lock, the count scans the whole record table,
    # and the load may go to the network. Each one says so before it starts, so
    # a stall is attributable to a named step instead of being a silent hang --
    # which is how one cost twelve minutes of diagnosis on 2026-09-01.
    print(f"  opening the index at {index}", flush=True)
    connection = open_store(index)
    print("  counting the records that still need a vector", flush=True)
    pending = connection.execute(
        load_sql("embed/pending_vectors"), (json.dumps(SEMANTIC_ROLES),)
    ).fetchall()
    if not pending:
        connection.close()
        print("  nothing to embed", flush=True)
        return 0
    print(f"  {len(pending):,} records to embed", flush=True)
    source = "from the local cache" if model_is_cached() else "downloading it, first run here"
    print(f"  loading the embedder: {MODEL_REPO} ({source})", flush=True)
    embedder = Embedder()
    batch_size = 256
    print(f"  embedder loaded; embedding in batches of {batch_size}", flush=True)
    written = 0
    processed = 0
    try:
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            matrix = embedder.embed([text for _, _, text in batch])
            rows = [(rid, sha) for rid, sha, _ in batch]
            written += commit_with_retry(
                connection, partial(write_vectors, connection, rows, matrix)
            )
            processed += len(batch)
            print(f"  embedded {written}/{len(pending)}", flush=True)
    finally:
        connection.close()
    if written < processed:
        print(
            f"  {processed - written} superseded mid-run and skipped; run embed again", flush=True
        )
    return 0

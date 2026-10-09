"""A refresh over an unchanged world writes nothing and embeds nothing.

The general property behind the pinned vector-cascade case: rewriting
unchanged conversations cascaded away every vector it touched, so an hourly
refresh paid a full re-embed -- 19,198 vectors, hours of CPU -- every hour.
The invariant is stronger than "vectors survive": an unchanged archive leaves
no trace of the pass at all.
"""

import json

import numpy as np
from load_test_sql import load_test_sql

from atrium.cli import main
from atrium.embed.semantic_roles import SEMANTIC_ROLES
from atrium.store.open_store import open_store
from atrium.store.write_vectors import write_vectors


def _write_archive(path, conversations):
    lines = [
        json.dumps({"kind": "rocket-agents-conversation-export", "records": len(conversations)})
    ]
    lines += [json.dumps(c) for c in conversations]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _conversation(conversation_id, text):
    return {
        "id": conversation_id,
        "source": "pi",
        "startedAt": "2026-08-01T00:00:00Z",
        "provenance": {"contentSha256": f"sha-{conversation_id}"},
        "events": [
            {
                "id": "e1",
                "kind": "message",
                "role": "assistant",
                "text": text,
            }
        ],
    }


def _notes_root(tmp_path):
    root = tmp_path / "notes"
    root.mkdir(exist_ok=True)
    (root / "one.md").write_text("# One\n\na durable note body")
    return root


def _snapshot(index):
    """Everything a write would disturb: rowids, revisions, vectors, pending."""
    connection = open_store(index, read_only=True)
    rows = connection.execute(
        load_test_sql("noop_refresh/select_record_revisions_by_rowid")
    ).fetchall()
    vectors = connection.execute(
        load_test_sql("noop_refresh/select_vector_record_ids_ordered")
    ).fetchall()
    placeholders = ",".join("?" for _ in SEMANTIC_ROLES)
    pending = connection.execute(
        load_test_sql("count_unembedded_semantic_records").format(placeholders=placeholders),
        tuple(SEMANTIC_ROLES),
    ).fetchone()[0]
    connection.close()
    return rows, vectors, pending


def test_a_refresh_over_an_unchanged_world_writes_and_embeds_nothing(tmp_path):
    archive, index = tmp_path / "a.jsonl", tmp_path / "i.sqlite3"
    _write_archive(
        archive,
        [_conversation("conv-a", "first sentinel passage"), _conversation("conv-b", "second one")],
    )
    root = _notes_root(tmp_path)
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    assert main(["--index", str(index), "ingest-notes", str(root)]) == 0

    # Embed the semantic layer, standing in for `atrium embed`.
    connection = open_store(index)
    placeholders = ",".join("?" for _ in SEMANTIC_ROLES)
    pending = connection.execute(
        load_test_sql("noop_refresh/select_semantic_record_revisions").format(
            placeholders=placeholders
        ),
        tuple(SEMANTIC_ROLES),
    ).fetchall()
    assert pending, "the notes must have produced a semantic record to embed"
    with connection:
        write_vectors(connection, pending, np.zeros((len(pending), 4), dtype=np.float32))
    connection.close()

    before = _snapshot(index)
    assert before[2] == 0, "everything semantic is embedded before the no-op pass"

    # The refresh chain again, over byte-identical inputs.
    assert main(["--index", str(index), "ingest", str(archive)]) == 0
    assert main(["--index", str(index), "ingest-notes", str(root)]) == 0

    after = _snapshot(index)
    assert after == before, "a no-op refresh must leave no trace: no new rowids, no lost vectors"
    assert after[2] == 0, "and nothing left to re-embed"

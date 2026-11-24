"""The resident service redacts credentials in what it answers, even from legacy raw records.

Records are written straight to the index, bypassing ingestion redaction, to
model rows indexed before the redactor existed. Sentinels are assembled at
run time, so this file holds no string a secret scanner would flag. The embedder
is a stub and the lane is lexical: redaction runs in ``render_hit`` after
ranking, so it does not depend on the models the real service keeps resident.
"""

import json
import shutil
import tempfile
import threading
from pathlib import Path

import pytest
from context_corpus import corpus as corpus  # noqa: PLC0414 -- explicit pytest fixture export

from atrium.record import Record
from atrium.serve.context_server import ContextServer
from atrium.serve.dense_matrix_holder import DenseMatrixHolder
from atrium.serve.request_context_service import request_context_service
from atrium.store.write_conversation import write_conversation

_ALNUM = "aB3dE5fG7hJ9kL2mN4pQ6rS8tU1vW3xY5zA7bC9dE2fG4hJ6kL8mN1pQ3rS5tU7vW9xY2zA4bC6"
_SECRETS = {
    "stripe": "sk_" + "live_" + _ALNUM[:24],
    "github": "gh" + "p_" + _ALNUM[:36],
    "private-key-body": "MII" + _ALNUM[:60],
    "url-password": "Zq9" + _ALNUM[:12] + "Xw",
    "table-cell": "tbl" + _ALNUM[:14],
    "assigned": "asg" + _ALNUM[:18],
}


def _texts() -> dict[str, str]:
    s = _SECRETS
    return {
        "history-token": f"canaryword the token is {s['stripe']} and {s['github']} here",
        "history-key": "canaryword -----BEGIN " + f"PRIVATE KEY-----\n{s['private-key-body']}\n"
        "-----END " + "PRIVATE KEY-----",
        "history-url": f"canaryword connect to postgres://admin:{s['url-password']}@db.invalid/app",
        "brain/canary.md": f"# Canary\n\ncanaryword\n\n| Password | `{s['table-cell']}` |\n\napi_key = {s['assigned']}",
    }


@pytest.fixture
def served(corpus):
    connection, project, state, index = corpus
    with connection:
        for name, text in _texts().items():
            curated = name.endswith(".md")
            write_conversation(
                connection,
                name,
                [
                    Record(
                        name,
                        name,
                        name,
                        "b" * 64,
                        "brain" if curated else "fixture",
                        "note" if curated else "user",
                        text,
                        None if curated else "2026-09-01T00:00:00Z",
                        None if curated else str(project),
                        None,
                        0,
                    )
                ],
            )
    # AF_UNIX paths are limited to about 104 bytes; pytest's tmp_path is longer.
    short = Path(tempfile.mkdtemp(prefix="atr", dir="/tmp"))
    holder = DenseMatrixHolder(index, short / "dense-matrix.npz")
    holder.prepare()

    class _Embedder:
        def embed(self, texts):
            raise AssertionError("the lexical lane must not embed")

    server = ContextServer(short / "context.sock", index, holder, _Embedder())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield project, state, index, short / "context.sock"
    server.shutdown()
    server.server_close()
    shutil.rmtree(short)


def test_the_resident_service_never_returns_a_credential(served):
    project, state, index, path = served
    reply = request_context_service(
        path,
        {
            "index": str(index),
            "query": "canaryword",
            "project": str(project),
            "limit": 8,
            "max_chars": 4000,
            "lane": "words",
            "state": str(state),
        },
        timeout=10,
    )
    # Every seeded record must have been retrieved, or the absence proves nothing.
    ids = {item["record_id"] for item in reply["evidence"]}
    assert len(ids) == 4, ids
    serialized = json.dumps(reply, ensure_ascii=False)
    for name, secret in _SECRETS.items():
        assert secret not in serialized, name
    assert "[REDACTED:" in serialized

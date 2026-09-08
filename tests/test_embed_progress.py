"""`atrium embed` must name each blocking step before it starts.

Every step of an embed run can sit at 0% CPU for minutes -- the open waits on
another writer, the count scans the record table, the load may reach the
network -- and on 2026-09-01 one did for twelve minutes while printing nothing,
which is indistinguishable from a hang. The lines below are what makes the next
occurrence legible, so their presence and their order around the load is the
thing under test.
"""

import numpy as np

from atrium.cli import main
from atrium.embed import embedder as embedder_module
from atrium.embed import model_is_cached as cache_module
from atrium.record import Record
from atrium.store.open_store import open_store
from atrium.store.write_conversation import write_conversation

_LOADING = "  <<loading>>"


class _FakeEmbedder:
    """Stands in for the 300 MB model, and marks the moment it is constructed."""

    def __init__(self):
        print(_LOADING, flush=True)

    def embed(self, texts):
        return np.tile(np.eye(1, 384, dtype=np.float32), (len(texts), 1))


def _index_with_one_pending_note(tmp_path):
    path = tmp_path / "index.sqlite3"
    connection = open_store(path)
    with connection:
        write_conversation(
            connection,
            "c",
            [
                Record(
                    record_id="r1",
                    event_id="e1",
                    conversation_id="c",
                    source_sha256="s",
                    provider="test",
                    role="note",
                    text="a note that still needs a vector",
                    authored_at=None,
                    workspace=None,
                    title=None,
                    event_index=0,
                )
            ],
        )
    connection.close()
    return path


def test_every_blocking_step_is_announced_in_order(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(embedder_module, "Embedder", _FakeEmbedder)
    monkeypatch.setattr(cache_module, "model_is_cached", lambda: True)
    path = _index_with_one_pending_note(tmp_path)

    assert main(["--index", str(path), "embed"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert any("opening the index" in line for line in lines)
    assert any("counting the records" in line for line in lines)
    assert any("1 records to embed" in line for line in lines)
    loading = next(i for i, line in enumerate(lines) if "loading the embedder" in line)
    assert "onnx-community/embeddinggemma-300m-ONNX" in lines[loading]
    assert "from the local cache" in lines[loading]
    # The announcement precedes the load itself, or it explains nothing: it is
    # the load that stalls.
    assert lines.index(_LOADING) == loading + 1
    # The stated batch size is the one the loop uses, or the line misdescribes
    # the wait it exists to explain.
    assert any("embedder loaded; embedding in batches of 256" in line for line in lines)
    assert any("embedded 1/1" in line for line in lines[loading:])


def test_an_uncached_model_says_it_is_downloading(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(embedder_module, "Embedder", _FakeEmbedder)
    monkeypatch.setattr(cache_module, "model_is_cached", lambda: False)
    path = _index_with_one_pending_note(tmp_path)

    assert main(["--index", str(path), "embed"]) == 0

    loading = next(
        line for line in capsys.readouterr().out.splitlines() if "loading the embedder" in line
    )
    assert "downloading it" in loading


def test_an_uncacheable_repo_is_reported_as_a_miss(monkeypatch):
    """Exercise the real `try_to_load_from_cache` contract, without the network.

    Both tests above monkeypatch `model_is_cached` away, so nothing else here
    would notice huggingface_hub changing its str-on-hit return: the probe would
    silently always answer "downloading it" and every assertion would still pass.
    A repo id that cannot be in any cache is a free way to reach the miss branch.
    """
    monkeypatch.setattr(cache_module, "MODEL_REPO", "atrium-test/no-such-model-repo")

    assert cache_module.model_is_cached() is False

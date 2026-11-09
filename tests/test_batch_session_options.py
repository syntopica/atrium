"""The refresh's batch embedding stops spinning; query embedding keeps the default."""

import numpy as np
import pytest
import tokenizers

from atrium.embed.batch_session_options import batch_session_options
from atrium.embed.embedder import Embedder

_SPINNING = "session.intra_op.allow_spinning"


class _Recorder:
    created: list[object] = []  # noqa: RUF012 -- a test stand-in's shared log

    def __init__(self, path, options=None, providers=None):
        _Recorder.created.append(options)

    def get_outputs(self):
        return [_Output()]

    def run(self, names, feed):
        return [np.ones((len(feed["input_ids"]), 768), dtype=np.float32)]


class _Output:
    name = "sentence_embedding"


class _Encoding:
    ids = (1,)
    attention_mask = (1,)


class _Tokenizer:
    @classmethod
    def from_file(cls, path):
        return cls()

    def enable_padding(self):
        pass

    def enable_truncation(self, **kwargs):
        pass

    def encode_batch(self, items):
        return [_Encoding() for _ in items]


def _fake_model(monkeypatch):
    import onnxruntime

    _Recorder.created = []
    monkeypatch.setattr(onnxruntime, "InferenceSession", _Recorder)
    monkeypatch.setattr(tokenizers, "Tokenizer", _Tokenizer)
    monkeypatch.setattr(
        "atrium.embed.cached_model_file.cached_model_file", lambda *args, **kwargs: "model"
    )


def test_batch_options_stop_spinning_and_keep_the_arena_off():
    options = batch_session_options()
    assert options.get_session_config_entry(_SPINNING) == "0"
    assert options.enable_cpu_mem_arena is False


def test_a_batch_embedder_runs_without_spinning(monkeypatch):
    _fake_model(monkeypatch)
    Embedder(batch=True).embed(["a"])
    assert [o.get_session_config_entry(_SPINNING) for o in _Recorder.created] == ["0"]


def test_the_default_embedder_keeps_spinning_for_query_latency(monkeypatch):
    _fake_model(monkeypatch)
    Embedder().embed(["a"])
    (options,) = _Recorder.created
    with pytest.raises(RuntimeError, match="does not have configuration"):
        options.get_session_config_entry(_SPINNING)

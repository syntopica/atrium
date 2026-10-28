"""Both resident models run without onnxruntime's CPU arena, which never shrinks."""

import time
from typing import ClassVar

import numpy as np
import tokenizers

from atrium.embed.cpu_session_options import cpu_session_options
from atrium.embed.embedder import Embedder
from atrium.rerank.cross_encoder import CrossEncoder


class _Recorder:
    """Stand-in session: records the options, answers one fixed shape."""

    created: ClassVar[list[object]] = []
    width = 1

    def __init__(self, path, options=None, providers=None):
        _Recorder.created.append(options)

    def get_inputs(self):
        return []

    def get_outputs(self):
        return [_Output()]

    def run(self, names, feed):
        return [np.ones((len(feed["input_ids"]), _Recorder.width), dtype=np.float32)]


class _Output:
    name = "sentence_embedding"


class _Encoding:
    ids = (1,)
    attention_mask = (1,)
    type_ids = (0,)
    offsets = ((0, 1),)


class _Tokenizer:
    @classmethod
    def from_file(cls, path):
        return cls()

    def enable_padding(self):
        pass

    def enable_truncation(self, **kwargs):
        pass

    def no_padding(self):
        pass

    def no_truncation(self):
        pass

    def encode(self, text, add_special_tokens=True):
        return _Encoding()

    def encode_batch(self, items):
        return [_Encoding() for _ in items]


def _fake_models(monkeypatch):
    import onnxruntime

    _Recorder.created = []
    _Recorder.width = 1
    monkeypatch.setattr(onnxruntime, "InferenceSession", _Recorder)
    monkeypatch.setattr(tokenizers, "Tokenizer", _Tokenizer)
    monkeypatch.setattr(
        "atrium.embed.cached_model_file.cached_model_file", lambda *args, **kwargs: "model"
    )


def test_the_options_turn_the_cpu_arena_off():
    assert cpu_session_options().enable_cpu_mem_arena is False


def test_the_embedder_session_runs_without_the_arena(monkeypatch):
    _fake_models(monkeypatch)
    _Recorder.width = 768
    Embedder().embed(["a"])
    assert [options.enable_cpu_mem_arena for options in _Recorder.created] == [False]


def test_the_reranker_session_runs_without_the_arena(monkeypatch):
    _fake_models(monkeypatch)
    CrossEncoder().score("q", ["a"], time.monotonic() + 60)
    assert [options.enable_cpu_mem_arena for options in _Recorder.created] == [False]

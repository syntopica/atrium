import numpy as np

from atrium.context.lazy_embedder import LazyEmbedder


class _Counting:
    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return np.full((len(texts), 2), float(self.calls), dtype=np.float32)


def test_a_repeated_query_is_embedded_once():
    model = _Counting()
    lazy = LazyEmbedder(lambda: model)
    first = lazy.embed(["q"])
    second = lazy.embed(["q"])
    assert model.calls == 1
    assert np.array_equal(first, second)


def test_only_the_last_call_is_kept():
    model = _Counting()
    lazy = LazyEmbedder(lambda: model)
    lazy.embed(["a"])
    lazy.embed(["b"])
    lazy.embed(["a"])
    assert model.calls == 3

"""Queries and stored documents are embedded under their own prompts."""

import numpy as np

from atrium.context.lazy_embedder import LazyEmbedder
from atrium.embed.document_prefix import DOCUMENT_PREFIX
from atrium.embed.embedder import Embedder
from atrium.embed.query_prefix import QUERY_PREFIX


class _Encoding:
    def __init__(self, text):
        self.ids = [len(text)]
        self.attention_mask = [1]


class _Tokenizer:
    def __init__(self):
        self.seen = []

    def encode_batch(self, texts):
        self.seen += texts
        return [_Encoding(text) for text in texts]


class _Session:
    def run(self, _, inputs):
        rows = len(inputs["input_ids"])
        return [None, np.ones((rows, 768), dtype=np.float32)]


def _loaded(embedder):
    tokenizer = _Tokenizer()
    embedder._tokenizer, embedder._session, embedder._output_index = tokenizer, _Session(), 1
    return tokenizer


def test_stored_vectors_keep_the_document_prompt():
    embedder = Embedder()
    tokenizer = _loaded(embedder)
    embedder.embed(["hola"])
    assert tokenizer.seen == [DOCUMENT_PREFIX + "hola"]


def test_a_query_embedder_uses_the_query_prompt(monkeypatch):
    built = []

    def factory():
        embedder = Embedder(QUERY_PREFIX)
        built.append(_loaded(embedder))
        return embedder

    monkeypatch.setattr("atrium.embed.query_embedder.query_embedder", factory)
    LazyEmbedder().embed(["donde vive el archivo"])
    assert built[0].seen == [QUERY_PREFIX + "donde vive el archivo"]

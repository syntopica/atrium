"""Score query-text pairs with bge-reranker-v2-m3 (ONNX, int8) on CPU."""

import threading
import time
from typing import TYPE_CHECKING

import numpy as np

from atrium.rerank.reranker_repo import RERANKER_REPO

if TYPE_CHECKING:
    import onnxruntime  # type: ignore[import-untyped]
    from tokenizers import Tokenizer

_ONNX_FILE = "model_quantized.onnx"
# Pairs are cut on the text side only, so the whole question always survives.
_MAX_LEN = 512
_BATCH_SIZE = 16


class CrossEncoder:
    """Lazy-loading CPU cross-encoder; safe to share between request threads.

    An onnxruntime session may run concurrently from several threads, and the
    tokenizer is read-only after load, so only loading takes the lock.
    """

    def __init__(
        self, repo: str = RERANKER_REPO, onnx_file: str = _ONNX_FILE, max_len: int = _MAX_LEN
    ) -> None:
        """Defer every heavy load; construction must stay cheap.

        ``repo`` and ``onnx_file`` (under the repository's ``onnx/``) name the
        model, so a candidate can be measured without editing this class.
        """
        self._repo = repo
        self._onnx_file = onnx_file
        self._max_len = max_len
        self._type_ids = False
        self._session: "onnxruntime.InferenceSession | None" = None  # noqa: UP037 -- TYPE_CHECKING-only import
        self._tokenizer: "Tokenizer | None" = None  # noqa: UP037 -- TYPE_CHECKING-only import
        self._load_lock = threading.Lock()

    def score(self, query: str, texts: list[str], deadline: float) -> list[float]:
        """Return one relevance logit per text, in input order.

        Checks ``deadline`` before each batch, so a slow machine costs at most
        one batch past it before the caller falls back to the fused order.
        """
        self._lazy_load()
        scores: list[float] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            if time.monotonic() > deadline:
                raise TimeoutError("rerank deadline passed")
            scores.extend(self._forward(query, texts[start : start + _BATCH_SIZE]))
        if not all(np.isfinite(scores)):
            raise RuntimeError("reranker produced a non-finite score")
        return scores

    def _forward(self, query: str, texts: list[str]) -> list[float]:
        assert self._tokenizer is not None
        assert self._session is not None
        encodings = self._tokenizer.encode_batch([(query, text) for text in texts])
        input_ids = np.asarray([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.asarray([e.attention_mask for e in encodings], dtype=np.int64)
        feed = {"input_ids": input_ids, "attention_mask": attention_mask}
        if self._type_ids:
            feed["token_type_ids"] = np.asarray([e.type_ids for e in encodings], dtype=np.int64)
        (logits,) = self._session.run(None, feed)
        return [float(value) for value in np.asarray(logits).reshape(-1)]

    def _lazy_load(self) -> None:
        if self._session is not None:
            return
        with self._load_lock:
            if self._session is not None:
                return  # type: ignore[unreachable]
            import onnxruntime
            from tokenizers import Tokenizer

            from atrium.embed.cached_model_file import cached_model_file

            model_path = cached_model_file(self._repo, self._onnx_file, subfolder="onnx")
            tokenizer = Tokenizer.from_file(cached_model_file(self._repo, "tokenizer.json"))
            tokenizer.enable_padding()
            tokenizer.enable_truncation(max_length=self._max_len, strategy="only_second")
            session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self._type_ids = any(one.name == "token_type_ids" for one in session.get_inputs())
            self._tokenizer = tokenizer
            self._session = session

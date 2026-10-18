"""Score query-text pairs with a multilingual cross-encoder (ONNX, int8) on CPU."""

import threading
import time
from typing import TYPE_CHECKING

import numpy as np

from atrium.rerank.cap_query_tokens import cap_query_tokens
from atrium.rerank.reranker_repo import RERANKER_REPO

if TYPE_CHECKING:
    import onnxruntime  # type: ignore[import-untyped]
    from tokenizers import Tokenizer

_ONNX_FILE = "model_quantized.onnx"
# Pairs are cut on the text side only, so a question of up to half the length
# survives whole; a longer one keeps its head (see cap_query_tokens).
# 256 kept the measured gain and halved the time against 512 (1.8 s vs 4.0 s
# median for 64 pairs on this Mac under load).
_MAX_LEN = 256
# The deadline is checked between batches only, and a population is 16
# candidates: at 16 one batch ran 6-7 s past a 3 s budget at load 100+ and the
# client's 7 s wait gave up (2026-10-18). At 4 the overshoot is a quarter of
# that for the same throughput (4.8 s vs 6.2 s for 16 pairs, same run).
# At load 44-81 (2026-10-19) one batch of 4 still took 7.1-7.4 s, past the
# whole 7 s wait on its own; one pair took 2.6 s at worst. One pair costs more
# CPU for a rerank that completes (21 vs 16 CPU-s for 16 pairs under that load,
# 2.1-2.3 vs 1.9-2.0 s wall at load 13, both inside the 3 s budget), but under
# load the rerank never completes, and then the larger batch is the waste.
_BATCH_SIZE = 1


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
        self._query_tokenizer: "Tokenizer | None" = None  # noqa: UP037 -- TYPE_CHECKING-only import
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
        assert self._query_tokenizer is not None
        assert self._session is not None
        query = cap_query_tokens(self._query_tokenizer, query, self._max_len // 2)
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
            tokenizer_path = cached_model_file(self._repo, "tokenizer.json")
            tokenizer = Tokenizer.from_file(tokenizer_path)
            tokenizer.enable_padding()
            tokenizer.enable_truncation(max_length=self._max_len, strategy="only_second")
            session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            self._type_ids = any(one.name == "token_type_ids" for one in session.get_inputs())
            self._tokenizer = tokenizer
            # Unpadded and untruncated: a pair-only truncation refuses a lone
            # query, and the file's own padding would count pad tokens.
            query_tokenizer = Tokenizer.from_file(tokenizer_path)
            query_tokenizer.no_padding()
            query_tokenizer.no_truncation()
            self._query_tokenizer = query_tokenizer
            self._session = session

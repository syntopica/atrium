"""Embed text with embeddinggemma-300m (ONNX, q8) on CPU, validating every vector."""

import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import onnxruntime  # type: ignore[import-untyped]
    from tokenizers import Tokenizer

# The model choice is measured, not preferred: the English-only default the
# previous system ran scored dense R@10 40.8% on a 365-pair set from this corpus
# (77% Spanish); this multilingual model scored 70.4% at the same 384 dims.
# CPU is required: on CoreML this model silently returns NaN or all-zero vectors
# without raising, which is why every batch is validated below.
_REPO = "onnx-community/embeddinggemma-300m-ONNX"
_ONNX_FILE = "model_quantized.onnx"
# The benchmark that produced the fusion weights embedded queries and documents
# through this same prefix, so changing it invalidates the measured 70/30.
_PREFIX = "task: sentence similarity | query: "
_DIM = 384  # Matryoshka truncation -- the first 384 of 768 dims
_MAX_LEN = 2048
# The ONNX graph has no internal batching; attention buffers grow superlinearly
# with padded length, so large unchunked batches can OOM. 32 is the batch size
# the previous system settled on for the same graph.
_BATCH_SIZE = 32


class Embedder:
    """Lazy-loading CPU embedder returning L2-normalized float32 vectors."""

    def __init__(self) -> None:
        """Defer every heavy load; construction must stay cheap."""
        self._session: "onnxruntime.InferenceSession | None" = None  # noqa: UP037 -- TYPE_CHECKING-only import
        self._tokenizer: "Tokenizer | None" = None  # noqa: UP037 -- TYPE_CHECKING-only import
        self._output_index: int | None = None
        self._load_lock = threading.Lock()

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return one normalized 384-dim vector per text, in input order.

        Raises rather than returning a degenerate vector: a NaN or all-zero row
        stored in the index is indistinguishable from a healthy one and poisons
        every query it appears in.
        """
        if not texts:
            return np.zeros((0, _DIM), dtype=np.float32)
        self._lazy_load()
        rows = [
            row
            for start in range(0, len(texts), _BATCH_SIZE)
            for row in self._forward(texts[start : start + _BATCH_SIZE])
        ]
        matrix = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1)
        if not np.all(np.isfinite(matrix)) or not np.all(norms > 0.0):
            raise RuntimeError(
                "embedder produced a NaN or all-zero vector -- refusing to store "
                "unusable vectors; check the onnxruntime installation"
            )
        # Typed local: on 3.11 numpy's stubs make the division Any and strict
        # mypy rejects returning it; the annotation pins what the gate checks.
        unit: np.ndarray = matrix / norms[:, np.newaxis]
        return unit

    def _forward(self, texts: list[str]) -> np.ndarray:
        assert self._tokenizer is not None
        assert self._session is not None
        encodings = self._tokenizer.encode_batch([_PREFIX + text for text in texts])
        input_ids = np.asarray([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.asarray([e.attention_mask for e in encodings], dtype=np.int64)
        outputs = self._session.run(
            None, {"input_ids": input_ids, "attention_mask": attention_mask}
        )
        result: np.ndarray = outputs[self._output_index][:, :_DIM]
        return result

    def _lazy_load(self) -> None:
        if self._session is not None:
            return
        with self._load_lock:
            if self._session is not None:
                return  # type: ignore[unreachable]
            import onnxruntime
            from tokenizers import Tokenizer

            from atrium.embed.cached_model_file import cached_model_file

            model_path = cached_model_file(_REPO, _ONNX_FILE, subfolder="onnx")
            cached_model_file(_REPO, _ONNX_FILE + "_data", subfolder="onnx")
            tokenizer_path = cached_model_file(_REPO, "tokenizer.json")

            session = onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            output_names = [output.name for output in session.get_outputs()]
            self._output_index = (
                output_names.index("sentence_embedding")
                if "sentence_embedding" in output_names
                else 1
            )
            tokenizer = Tokenizer.from_file(tokenizer_path)
            tokenizer.enable_padding()
            tokenizer.enable_truncation(max_length=_MAX_LEN)
            self._tokenizer = tokenizer
            self._session = session

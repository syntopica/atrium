"""The pinned Hugging Face repository the reranker model is loaded from."""

# Alibaba's gte-multilingual-reranker-base (Apache-2.0), in the ONNX export
# onnx-community publishes. Measured 2026-10-15 end to end (R/MRR at 8, 85
# acceptance | 88 held-out questions, production 0.28/0.12 | 0.43/0.29): at 256
# tokens 0.39/0.22 | 0.50/0.39, the same gain as bge-reranker-v2-m3 at 2.5x
# its speed. jina-reranker-v2 is CC-BY-NC-4.0, so it is not an option.
RERANKER_REPO = "onnx-community/gte-multilingual-reranker-base"

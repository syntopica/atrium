"""The pinned Hugging Face repository the reranker model is loaded from."""

# BAAI's bge-reranker-v2-m3 (Apache-2.0), multilingual like the corpus, in the
# ONNX export onnx-community publishes. jina-reranker-v2 measured close but is
# CC-BY-NC-4.0, so it is not an option.
RERANKER_REPO = "onnx-community/bge-reranker-v2-m3-ONNX"

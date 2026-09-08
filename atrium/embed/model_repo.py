"""The pinned Hugging Face repository the embedding model is loaded from."""

# Shared rather than private to the embedder because the CLI names it before
# the load: a stall in a step nobody announced is indistinguishable from a hang.
MODEL_REPO = "onnx-community/embeddinggemma-300m-ONNX"

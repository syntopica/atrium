"""Report whether the embedding model is already on this machine."""

from huggingface_hub import try_to_load_from_cache

from atrium.embed.model_repo import MODEL_REPO

# Every file the embedder's load reaches for. Checking only the weights would
# call an interrupted first run "cached" and then stall on the external data
# file -- exactly the silent wait this progress line exists to explain. Naming
# the files here rather than asking the embedder keeps this a question about
# the cache, answerable without loading anything; the worst a drift in a
# filename costs is a wrong word in one progress line, never a failed load.
_REQUIRED_FILES = (
    "onnx/model_quantized.onnx",
    "onnx/model_quantized.onnx_data",
    "tokenizer.json",
)


def model_is_cached() -> bool:
    """True when the model can be loaded without reaching the network.

    `try_to_load_from_cache` returns the path on a hit and a sentinel object
    otherwise, and never contacts the Hub, so asking is free.
    """
    return all(
        isinstance(try_to_load_from_cache(MODEL_REPO, name), str) for name in _REQUIRED_FILES
    )

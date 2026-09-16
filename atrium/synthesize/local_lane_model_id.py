"""The population name a local-lane run writes into every job key."""


def local_lane_model_id(model: str) -> str:
    """Name the population for ``model`` served by a local Ollama.

    The transport is part of the name, as it is for the cursor lane: the same
    weights answer differently behind another runtime, and a population is
    what the recipe ranks. The tag's colon would be noise in a job key, so it
    becomes a dash: `qwen3.6:35b-mlx` is `ollama-qwen3.6-35b-mlx`.
    """
    return "ollama-" + model.replace(":", "-")

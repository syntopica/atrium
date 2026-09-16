"""The population name an agy-lane run writes into every job key."""

from atrium.synthesize.agy_lane_call import AGY_MODEL_ID


def agy_lane_model_id(model: str) -> str:
    """Name the population for ``model`` behind the Antigravity transport.

    The default model keeps its bare name: `gemini-3.7-flash-medium` is the
    population name in every job key and manifest written since the lane
    existed, and renaming it would orphan those records. Any other model is
    prefixed with the transport, as the cursor lane does, so the same model
    through two transports is two jobs.
    """
    return model if model == AGY_MODEL_ID else f"agy-{model}"

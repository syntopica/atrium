"""The population name an agy-lane run writes into every job key."""

from atrium.synthesize.legacy_agy_population import LEGACY_AGY_POPULATION


def agy_lane_model_id(model: str) -> str:
    """Name the population for ``model`` behind the Antigravity transport.

    Every model is prefixed with the transport, as the cursor lane does and as
    the worker names its agy runs, so the same model through two transports is
    two jobs. The one exception is the lane's first default, whose bare name
    is in every job key written before 2026-10-15: renaming it would orphan
    those records.
    """
    return model if model == LEGACY_AGY_POPULATION else f"agy-{model}"

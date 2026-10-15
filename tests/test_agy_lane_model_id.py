"""The first agy population keeps its historical name; every other model is prefixed."""

from atrium.synthesize.agy_lane_call import AGY_MODEL_ID
from atrium.synthesize.agy_lane_model_id import agy_lane_model_id


def test_the_legacy_population_keeps_the_name_in_every_existing_job_key() -> None:
    assert agy_lane_model_id("gemini-3.7-flash-medium") == "gemini-3.7-flash-medium"


def test_the_current_default_is_a_new_prefixed_population() -> None:
    assert agy_lane_model_id(AGY_MODEL_ID) == "agy-gemini-3.8-flash-medium"


def test_another_model_carries_the_transport() -> None:
    assert agy_lane_model_id("claude-sonnet-4-6") == "agy-claude-sonnet-4-6"

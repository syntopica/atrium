"""The default agy population keeps its historical name; other models are prefixed."""

from atrium.synthesize.agy_lane_call import AGY_MODEL_ID
from atrium.synthesize.agy_lane_model_id import agy_lane_model_id


def test_the_default_model_keeps_the_name_in_every_existing_job_key() -> None:
    assert agy_lane_model_id(AGY_MODEL_ID) == "gemini-3.7-flash-medium"


def test_another_model_carries_the_transport() -> None:
    assert agy_lane_model_id("claude-sonnet-4-6") == "agy-claude-sonnet-4-6"

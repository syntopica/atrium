"""The transport is part of the population name, so lanes never share a job."""

from atrium.synthesize.cursor_lane_model_id import cursor_lane_model_id
from atrium.synthesize.job_identity import job_identity


def test_the_transport_prefixes_the_model() -> None:
    assert cursor_lane_model_id("gemini-3.7-flash-high") == "cursor-gemini-3.7-flash-high"


def test_the_same_model_through_another_transport_is_another_job() -> None:
    args = ("conv", "rev", "episode")
    through_cursor = job_identity(*args, cursor_lane_model_id("gemini-3.7-flash-medium"))
    through_agy = job_identity(*args, "gemini-3.7-flash-medium")
    assert through_cursor != through_agy

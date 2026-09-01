"""A pinned model is a different population, never a silent overwrite."""

from atrium.synthesize.codex_lane_call import CODEX_MODEL_ID
from atrium.synthesize.codex_lane_model_id import codex_lane_model_id
from atrium.synthesize.job_identity import job_identity


def test_an_unpinned_run_keeps_the_historical_population_name():
    """Renaming it would orphan the 10,967 records already produced under it."""
    assert codex_lane_model_id(None, None) == CODEX_MODEL_ID


def test_model_and_effort_both_name_the_population():
    assert codex_lane_model_id("gpt-5.6-terra", "low") == "gpt-5.6-terra-low"
    assert codex_lane_model_id("gpt-5.6-terra", None) == "gpt-5.6-terra"
    assert codex_lane_model_id(None, "low") == f"{CODEX_MODEL_ID}-low"


def test_a_different_model_is_a_different_job_for_the_same_episode():
    """The model id enters the job key, so two populations coexist rather than
    one overwriting the other's paid-for output."""
    args = ("conv", "rev", "episode")
    cheap = job_identity(*args, codex_lane_model_id("gpt-5.6-terra", "low"))
    rich = job_identity(*args, codex_lane_model_id("gpt-5.6-sol", "high"))
    default = job_identity(*args, codex_lane_model_id(None, None))
    assert len({cheap, rich, default}) == 3

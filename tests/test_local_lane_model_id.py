"""The local lane names its own population, tag and all."""

from atrium.synthesize.job_identity import job_identity
from atrium.synthesize.local_lane_model_id import local_lane_model_id


def test_the_tag_becomes_part_of_the_name() -> None:
    assert local_lane_model_id("qwen3.6:35b-mlx") == "ollama-qwen3.6-35b-mlx"


def test_the_gguf_build_of_one_model_is_another_population() -> None:
    args = ("conv", "rev", "episode")
    mlx = job_identity(*args, local_lane_model_id("qwen3.6:35b-mlx"))
    gguf = job_identity(*args, local_lane_model_id("qwen3.6:35b"))
    assert mlx != gguf

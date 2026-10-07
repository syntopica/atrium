"""Each `--producer` value selects its own lane, key and queue."""

import pytest

from atrium.synthesis_pass.select_producer_lane import select_producer_lane
from atrium.synthesize.agy_lane_call import AGY_MODEL_ID
from atrium.synthesize.agy_lane_model_id import agy_lane_model_id
from atrium.synthesize.codex_lane_model_id import codex_lane_model_id
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL
from atrium.synthesize.local_lane_model_id import local_lane_model_id
from atrium.synthesize.worker_lane_call import WORKER_SYNTHESIS_QUEUE
from atrium.synthesize.worker_task_lane_call import (
    WORKER_TASK_DEFAULT_PROFILE,
    WORKER_TASK_QUEUE,
)
from atrium.synthesize.worker_task_lane_model_id import worker_task_lane_model_id


def test_agy_is_the_fallback_lane() -> None:
    lane = select_producer_lane("agy", None, None)
    assert lane.model_id == agy_lane_model_id(AGY_MODEL_ID)
    assert lane.worker_queue is None
    assert lane.journaled_call is None


def test_agy_honours_a_pinned_model() -> None:
    assert select_producer_lane("agy", "m", None).model_id == agy_lane_model_id("m")


def test_codex_keys_on_model_and_effort() -> None:
    lane = select_producer_lane("codex", "gpt-x", "high")
    assert lane.model_id == codex_lane_model_id("gpt-x", "high")
    assert lane.worker_queue is None


def test_local_is_direct_without_the_worker_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATRIUM_LOCAL_TRANSPORT", raising=False)
    lane = select_producer_lane("local", None, None)
    assert lane.model_id == local_lane_model_id(LOCAL_DEFAULT_MODEL)
    assert lane.worker_queue is None
    assert lane.journaled_call is None


def test_local_through_the_worker_journals_its_submissions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATRIUM_LOCAL_TRANSPORT", "worker")
    lane = select_producer_lane("local", "m", None)
    assert lane.model_id == local_lane_model_id("m")
    assert lane.worker_queue == WORKER_SYNTHESIS_QUEUE
    assert lane.journaled_call is not None


def test_task_lane_uses_the_task_queue_and_profile() -> None:
    lane = select_producer_lane("task", None, None)
    assert lane.model_id == worker_task_lane_model_id(WORKER_TASK_DEFAULT_PROFILE)
    assert lane.worker_queue == WORKER_TASK_QUEUE
    assert lane.journaled_call is not None

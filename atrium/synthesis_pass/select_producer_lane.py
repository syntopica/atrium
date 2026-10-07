"""Map the `--producer` flag to its lane."""

from atrium.synthesis_pass.agy_producer_lane import agy_producer_lane
from atrium.synthesis_pass.codex_producer_lane import codex_producer_lane
from atrium.synthesis_pass.local_producer_lane import local_producer_lane
from atrium.synthesis_pass.max_producer_lane import max_producer_lane
from atrium.synthesis_pass.producer_lane import ProducerLane
from atrium.synthesis_pass.task_producer_lane import task_producer_lane


def select_producer_lane(producer: str, model: str | None, effort: str | None) -> ProducerLane:
    """Any name that is not max, codex, local or task is the agy default."""
    if producer == "max":
        return max_producer_lane()
    if producer == "codex":
        return codex_producer_lane(model, effort)
    if producer == "local":
        return local_producer_lane(model)
    if producer == "task":
        return task_producer_lane(model)
    return agy_producer_lane(model)

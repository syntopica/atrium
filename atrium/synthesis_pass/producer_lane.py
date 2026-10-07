"""A chosen synthesis lane: how to call it, what it is keyed as, and its queue."""

from dataclasses import dataclass

from atrium.synthesis_pass.journaled_producer import JournaledProducer
from atrium.synthesize.producer import Producer


@dataclass(frozen=True)
class ProducerLane:
    """``journaled_call`` and ``worker_queue`` exist only for the worker lanes."""

    call: Producer
    model_id: str
    journaled_call: JournaledProducer | None = None
    worker_queue: str | None = None

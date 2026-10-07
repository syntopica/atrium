"""A worker-lane producer that reports each job it submits."""

from typing import Any, Protocol


class JournaledProducer(Protocol):
    """Like a producer, plus the ``on_submit`` hook the journal listens on."""

    def __call__(
        self, system_text: str, user_text: str, tool: dict[str, Any], on_submit: Any
    ) -> dict[str, Any]:
        """Produce one result, calling ``on_submit`` with each submitted job."""
        ...

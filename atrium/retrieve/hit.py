"""One retrieval result."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Hit:
    """A retrieved record with the score and the lane that found it.

    ``lane`` is kept on every hit because the fused list is not allowed to be the
    only output: on queries that share no informative word with their answer,
    lexical retrieval scores 0% and fusion demotes the dense signal that is the
    only one working (12% -> 8% R@10 measured). A caller that cannot see which
    lane produced a hit cannot honour that.
    """

    record_id: str
    text: str
    score: float
    lane: str
    conversation_id: str
    source_sha256: str
    authored_at: str | None
    provider: str

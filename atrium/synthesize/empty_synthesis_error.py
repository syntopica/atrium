"""Raised when a producer answers with nothing worth keeping; the record is not written."""


class EmptySynthesisError(RuntimeError):
    """The producer returned neither a title nor a summary.

    An empty output is a failed call, not a memory: written to the registry it
    counts as the episode's served record, blocks every later population from
    synthesizing the episode, and produces no index row -- exactly one such
    record sat in `gpt-5.6-terra-low` reporting `1 NOT IN INDEX` on 77
    consecutive refreshes. Failing the conversation instead leaves the episode
    pending, so the next pass pays for it again and gets a real answer.
    """

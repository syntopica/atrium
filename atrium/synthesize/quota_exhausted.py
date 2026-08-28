"""Raised when a producer's quota window is exhausted; the pass should stop."""


class QuotaExhausted(RuntimeError):
    """The lane's quota is spent until its reset; retrying now cannot succeed."""

"""Session options for a background batch run: no CPU arena, no spinning threads."""

from typing import TYPE_CHECKING

from atrium.embed.cpu_session_options import cpu_session_options

if TYPE_CHECKING:
    import onnxruntime  # type: ignore[import-untyped]


def batch_session_options() -> "onnxruntime.SessionOptions":
    """Return the resident options with intra-op spinning turned off.

    An idle onnxruntime worker thread spins waiting for work, and on a machine
    other sessions keep busy that burns cores for nothing. Measured on the
    MacBook at load 14-16 (2026-11-09), embedding 64 texts with every core:
    spinning 3.3-3.5 s wall and 25-26 CPU-s, not spinning 2.9 s and 16.5
    CPU-s. The reranker lost 10-15% latency the same way (1.7-1.9 s against
    1.9-2.4 s for 64 pairs), and its answer races a 3 s budget, so only the
    refresh's batch embedding uses these.
    """
    options = cpu_session_options()
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    return options

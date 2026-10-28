"""Session options for an onnxruntime model that lives in a long-running process."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import onnxruntime  # type: ignore[import-untyped]


def cpu_session_options() -> "onnxruntime.SessionOptions":
    """Return options with the CPU memory arena off.

    The arena keeps every block it ever allocated and never hands memory back.
    Queries and texts vary in length, and the resident context service runs
    them concurrently, so the arena keeps growing to new peaks: the service on
    the MacBook reached a 23 GB footprint in a day, and with its other jobs that
    was enough to reset the machine on watchdog (2026-10-27). A probe of 300
    requests, 8 at a time, grew from 2.5 to 8.4 GB with the arena on. With it
    off, the footprint fell back to 1.7-3 GB between bursts, and the run took
    about the same time (8:56 vs 8:47) (2026-10-28).
    """
    import onnxruntime

    options = onnxruntime.SessionOptions()
    options.enable_cpu_mem_arena = False
    return options

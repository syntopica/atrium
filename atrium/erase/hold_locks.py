"""Hold the instance's writer locks for the duration of a block."""

import fcntl
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path


@contextmanager
def hold_locks(paths: Sequence[Path]) -> Iterator[None]:
    """Take every lock exclusively without waiting, or raise ``BlockingIOError``.

    The same flock(2) files ``atrium-lock`` holds for the refresh and the
    synthesis pass, so no ingest can write back a row, and no pass re-synthesize
    a record, between reading the registry and the erasure's delete.
    """
    with ExitStack() as stack:
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(path.open("a"))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield

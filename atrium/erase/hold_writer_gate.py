"""Take the erase lock shared for the life of one writing command."""

import fcntl
from pathlib import Path
from typing import TextIO

from atrium.erase.erase_lock_file import erase_lock_file


def hold_writer_gate(state: Path) -> TextIO:
    """Return the open handle holding the lock shared, or raise ``BlockingIOError``.

    Shared, so writers never wait on each other; non-blocking, so a writer that
    meets an erase in progress refuses at once instead of hanging a hook. It is
    a lock of its own rather than the refresh or synthesis lock: those are held
    by the `atrium-lock` wrapper around the commands that run here, and a fresh
    `flock` on the same file from a child conflicts with its parent's. The
    handle must stay referenced while the command writes; closing it releases.
    """
    path = erase_lock_file(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a")
    try:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise
    return handle

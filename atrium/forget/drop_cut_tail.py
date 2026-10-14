"""Remove a final line that a crash left without its newline."""

import os
from typing import BinaryIO


def drop_cut_tail(handle: BinaryIO) -> None:
    """Truncate the file after its last newline; a complete file is unchanged.

    The fragment was never acknowledged: the append that wrote it did not
    return, so dropping it loses nothing a caller relied on.
    """
    size = handle.seek(0, os.SEEK_END)
    if size == 0:
        return
    handle.seek(size - 1)
    if handle.read(1) == b"\n":
        return
    handle.seek(0)
    keep = handle.read().rfind(b"\n") + 1
    handle.truncate(keep)

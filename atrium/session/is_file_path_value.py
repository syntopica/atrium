"""Tell a labelled file path from a credential."""

import re

from atrium.session.file_path_min_segments import FILE_PATH_MIN_SEGMENTS


def is_file_path_value(value: str) -> bool:
    """Whether the value is slash-separated segments ending in a file extension.

    An object-storage listing prints ``key: 'exports/raw/2026-10-20/manifest.json'``,
    which the inline rule read as a ``key`` holding a token. Base64 keys hold
    slashes, but not three non-empty segments ending in ``.json``.
    """
    segments = value.split("/")
    return (
        len(segments) >= FILE_PATH_MIN_SEGMENTS
        and all(segments)
        and re.search(r"\.[A-Za-z]{2,5}$", value) is not None
    )

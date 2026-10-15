"""The word-index phrase that finds episodes naming one file."""

from pathlib import PurePosixPath

from atrium.recall.generic_file_names import GENERIC_FILE_NAMES


def file_phrase(relative_path: str) -> str | None:
    """Return an FTS5 phrase for the file, or None when nothing names it.

    The file name alone, quoted, so the word tokenizer splits it the way it
    split the stored text (`retrieve_context.py` is the phrase `retrieve
    context py`). A generic name takes its parent directory along, and a
    generic name at the root names nothing worth matching.
    """
    path = PurePosixPath(relative_path)
    name = path.name
    if not name:
        return None
    text = name
    if name.lower() in GENERIC_FILE_NAMES:
        if path.parent.name in ("", "."):
            return None
        text = f"{path.parent.name}/{name}"
    return '"' + text.replace('"', '""') + '"'

"""Turn a Hugging Face cache symlink into a real file in the snapshot directory."""

import os
import shutil
from pathlib import Path


def materialized_model_file(path: str) -> str:
    """Return ``path`` after making it a real file rather than a symlink.

    onnxruntime resolves symlinks before it checks that a model's external data
    sits in the model's own directory. huggingface-hub 2.x keeps each blob in
    its own `blobs/<prefix>/` directory, so the model and its `.onnx_data`
    resolve to different directories and the load is refused with `External
    data path escapes model directory` on every freshly filled cache. A hard
    link to the blob costs no space and is a layout the cache already uses
    where symlinks are unavailable; the copy covers a blob on another volume.
    """
    link = Path(path)
    if not link.is_symlink():
        return path
    blob = link.resolve(strict=True)
    staged = link.with_name(f"{link.name}.{os.getpid()}.materializing")
    try:
        os.link(blob, staged)
    except OSError:
        shutil.copyfile(blob, staged)
    staged.replace(link)
    return path

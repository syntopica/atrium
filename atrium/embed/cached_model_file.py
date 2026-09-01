"""Resolve one model file, preferring the cache over the network."""

from huggingface_hub import hf_hub_download


def cached_model_file(repo: str, filename: str, subfolder: str | None = None) -> str:
    """Return the local path to a pinned model file, cache first.

    The model is pinned by repo and filename and never changes, so a cached
    copy is always the right answer. `hf_hub_download` nonetheless contacts the
    Hub to revalidate the etag even on a cache hit, which turns a stalled or
    absent network into something indistinguishable from a hang: `atrium embed`
    sat at 0% CPU for twelve minutes, printing nothing, on 2026-09-01.

    A memory that answers from a local index has no business requiring the
    network to read a file it already has. Ask the cache, and reach the network
    only when the file genuinely is not there.
    """
    try:
        return hf_hub_download(repo, filename=filename, subfolder=subfolder, local_files_only=True)
    except OSError:
        # Not cached (huggingface raises a LocalEntryNotFoundError, an OSError)
        # -- the first run on a machine has to download it.
        return hf_hub_download(repo, filename=filename, subfolder=subfolder)

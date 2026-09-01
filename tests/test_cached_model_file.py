"""The embedder must not need the network to read a file it already has.

Measured 2026-09-01 against an endpoint that drops packets rather than
refusing them: loading the embedder took 34.2 s instead of 1.4 s, because
`hf_hub_download` revalidates the etag before falling back to the cache. Three
such calls plus retries is how `atrium embed` sat at 0% CPU printing nothing.
"""

import pytest

from atrium.embed import cached_model_file as module
from atrium.embed.cached_model_file import cached_model_file


def test_a_cached_file_never_reaches_the_network(monkeypatch):
    calls = []

    def fake(repo, filename, subfolder=None, local_files_only=False):
        calls.append(local_files_only)
        if not local_files_only:
            raise AssertionError("went to the network for a file already cached")
        return "/cache/model.onnx"

    monkeypatch.setattr(module, "hf_hub_download", fake)
    assert cached_model_file("repo", "model.onnx", subfolder="onnx") == "/cache/model.onnx"
    assert calls == [True]


def test_a_missing_file_still_downloads(monkeypatch):
    """The first run on a machine has nothing cached and must fetch."""
    calls = []

    def fake(repo, filename, subfolder=None, local_files_only=False):
        calls.append(local_files_only)
        if local_files_only:
            raise OSError("not in cache")
        return "/downloaded/model.onnx"

    monkeypatch.setattr(module, "hf_hub_download", fake)
    assert cached_model_file("repo", "model.onnx") == "/downloaded/model.onnx"
    assert calls == [True, False]


def test_a_download_failure_is_not_swallowed(monkeypatch):
    """A machine with neither cache nor network must say so, not return junk."""

    def fake(repo, filename, subfolder=None, local_files_only=False):
        raise OSError("no cache, no network")

    monkeypatch.setattr(module, "hf_hub_download", fake)
    with pytest.raises(OSError, match="no cache, no network"):
        cached_model_file("repo", "model.onnx")

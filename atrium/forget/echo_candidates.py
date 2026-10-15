"""Find the synthesis records written about a lone harness echo."""

from collections.abc import Mapping
from pathlib import Path

from atrium.ingest.read_archive import read_archive
from atrium.synthesize.harness_echoes import HARNESS_ECHOES


def echo_candidates(archive: Path, episodes: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    """Return synthesis record id to the echo its only event carries.

    The event text is read from the archive, not the index: the raw ingest
    turns many of these echoes away as tool results, so the index cannot say
    what a single-event episode was about. One streamed pass, about 20 s on the
    live archive of 2026-10-16.
    """
    found: dict[str, str] = {}
    for conversation in read_archive(archive):
        wanted = episodes.get(conversation["id"])
        if not wanted:
            continue
        for event in conversation.get("events") or []:
            record_id = wanted.get(event.get("id"))
            text = (event.get("text") or "").strip()
            if record_id and text in HARNESS_ECHOES:
                found[record_id] = text
    return found

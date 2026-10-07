"""The deterministic token proxy episode segmentation uses."""

from typing import Any

from atrium.synthesize.episode_word import EPISODE_WORD

# Deterministic token proxy, part of the fingerprint: one token per word or
# ~4 characters, whichever is larger. A real tokenizer here would tie episode
# boundaries to a model artifact's exact version for no boundary quality gain.
_CHARS_PER_TOKEN = 4


def token_estimate(event_indexes: list[int], events: list[dict[str, Any]]) -> int:
    """Return the estimated token count of the given events' text."""
    total = 0
    for index in event_indexes:
        text = events[index].get("text") or ""
        total += max(len(EPISODE_WORD.findall(text)), len(text) // _CHARS_PER_TOKEN)
    return total

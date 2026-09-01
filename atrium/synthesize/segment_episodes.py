"""Cut a conversation into episodes -- `episode-texttiling-v1`, deterministic."""

import math
import re
from collections import Counter
from typing import Any

from atrium.synthesize.stopwords import SPANISH_ENGLISH_STOPWORDS
from atrium.synthesize.turn_blocks import turn_blocks

SEGMENTATION_FINGERPRINT = "episode-texttiling-v1"

_WINDOW = 3  # turn blocks on each side of a candidate boundary
_MIN_BLOCKS_BETWEEN_CUTS = 2
_TOKEN_CEILING = 32_000
# Deterministic token proxy, part of the fingerprint: one token per word or
# ~4 characters, whichever is larger. A real tokenizer here would tie episode
# boundaries to a model artifact's exact version for no boundary quality gain.
_CHARS_PER_TOKEN = 4

_WORD = re.compile(r"[^\W_]{2,}", re.UNICODE)


def segment_episodes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return episodes covering all events, each with its map chunks.

    An episode is `{"event_indexes": [...], "chunks": [[...], ...]}`. For
    almost every episode `chunks` is one list equal to `event_indexes`; only
    an episode over the token ceiling is mechanically split into several map
    chunks, which exist for model-context reasons and are never retrieval
    episodes -- the reduce step folds them back into one synthesis.

    Cuts happen at (1) explicit reset markers and (2) TextTiling similarity
    valleys over the human turns whose depth exceeds the session's median
    depth plus one MAD, with at least two human turns between cuts. Only
    human text feeds topic detection, so a tool dump cannot fake a shift.
    """
    blocks = turn_blocks(events)
    if not blocks:
        return []
    cuts = _reset_cuts(blocks) | _valley_cuts(blocks)
    return [
        {
            "event_indexes": episode,
            "chunks": _enforce_ceiling(episode, blocks, events),
        }
        for episode in _split_at(blocks, cuts)
    ]


def _reset_cuts(blocks: list[dict[str, Any]]) -> set[int]:
    return {index for index, block in enumerate(blocks) if block["resets"] and index > 0}


def _valley_cuts(blocks: list[dict[str, Any]]) -> set[int]:
    vectors = [_tf_vector(block["human_text"]) for block in blocks]
    idf = _idf(vectors)
    depths: dict[int, float] = {}
    for boundary in range(1, len(blocks)):
        left = _merge(vectors[max(0, boundary - _WINDOW) : boundary])
        right = _merge(vectors[boundary : boundary + _WINDOW])
        depths[boundary] = 1.0 - _cosine(left, right, idf)
    if not depths:
        return set()
    values = sorted(depths.values())
    median = values[len(values) // 2]
    mad = sorted(abs(value - median) for value in values)[len(values) // 2]
    threshold = median + mad
    cuts: set[int] = set()
    last_cut = 0
    for boundary in sorted(depths):
        if depths[boundary] > threshold and boundary - last_cut >= _MIN_BLOCKS_BETWEEN_CUTS:
            cuts.add(boundary)
            last_cut = boundary
    return cuts


def _split_at(blocks: list[dict[str, Any]], cuts: set[int]) -> list[list[int]]:
    episodes: list[list[int]] = [[]]
    for index, block in enumerate(blocks):
        if index in cuts and episodes[-1]:
            episodes.append([])
        episodes[-1].extend(block["event_indexes"])
    return [episode for episode in episodes if episode]


def _enforce_ceiling(
    episode: list[int], blocks: list[dict[str, Any]], events: list[dict[str, Any]]
) -> list[list[int]]:
    if _tokens(episode, events) <= _TOKEN_CEILING:
        return [episode]
    boundaries = {block["event_indexes"][0] for block in blocks}
    chunks: list[list[int]] = [[]]
    for event_index in episode:
        over = chunks[-1] and _tokens(chunks[-1], events) > _TOKEN_CEILING
        # Prefer cutting at a human boundary, but a single block bigger than
        # the whole ceiling (one 600k-char paste) must still split -- events
        # stay atomic, blocks do not.
        if over and (event_index in boundaries or _tokens(chunks[-1], events) > 2 * _TOKEN_CEILING):
            chunks.append([])
        chunks[-1].append(event_index)
    return [chunk for chunk in chunks if chunk]


def _tokens(event_indexes: list[int], events: list[dict[str, Any]]) -> int:
    total = 0
    for index in event_indexes:
        text = events[index].get("text") or ""
        total += max(len(_WORD.findall(text)), len(text) // _CHARS_PER_TOKEN)
    return total


def _tf_vector(text: str) -> Counter[str]:
    words = [
        word.lower()
        for word in _WORD.findall(text)
        if word.lower() not in SPANISH_ENGLISH_STOPWORDS
    ]
    return Counter(words)


def _idf(vectors: list[Counter[str]]) -> dict[str, float]:
    documents = max(len(vectors), 1)
    frequency: Counter[str] = Counter()
    for vector in vectors:
        frequency.update(set(vector))
    return {word: math.log(documents / (1 + count)) + 1.0 for word, count in frequency.items()}


def _merge(vectors: list[Counter[str]]) -> Counter[str]:
    merged: Counter[str] = Counter()
    for vector in vectors:
        merged.update(vector)
    return merged


def _cosine(left: Counter[str], right: Counter[str], idf: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right[word] * idf.get(word, 1.0) ** 2 for word, count in left.items())
    norm_left = math.sqrt(sum((count * idf.get(word, 1.0)) ** 2 for word, count in left.items()))
    norm_right = math.sqrt(sum((count * idf.get(word, 1.0)) ** 2 for word, count in right.items()))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)

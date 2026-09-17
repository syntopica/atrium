"""Stage three: the numeric veto, the pair judge and clique-only clustering."""

from typing import Any

import numpy as np
import pytest

from atrium.curate import pair_relation as pair_relation_module
from atrium.curate.claim_pairs import claim_pairs
from atrium.curate.equivalence_clusters import equivalence_clusters
from atrium.curate.numeric_signature import numeric_signature
from atrium.curate.pair_relation import pair_relation


class _Embedder:
    """Two claims share a vector when their first letter matches.

    Deterministic on purpose: `hash()` of a string is salted per process, so a
    fixture built on it passes and fails on alternate runs.
    """

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            vector = np.zeros(4, dtype=np.float32)
            vector[ord(text[0]) % 4] = 1.0
            rows.append(vector)
        return np.asarray(rows, dtype=np.float32)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("38 orphans held 7.4 GB", "3 orphans held 7.4 GB"),
        ("the flag is enabled", "the flag is not enabled"),
        ("pnpm 1.2 is pinned", "pnpm 1-2 is pinned"),
        ("the check is x >= 3", "the check is x < 3"),
        ("Node v26.5.1 was used", "Node v26.5.0 was used"),
    ],
)
def test_different_quantities_have_different_signatures(first: str, second: str) -> None:
    assert numeric_signature(first) != numeric_signature(second)


def test_a_reordered_paraphrase_keeps_its_signature() -> None:
    assert numeric_signature("38 orphans held 7.4 GB") == numeric_signature(
        "7.4 GB were held by 38 orphans"
    )


def test_the_signature_overrules_an_equivalent_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model calling two different measurements the same must not merge them."""

    def fake_call(*_: Any, **__: Any) -> dict[str, Any]:
        return {
            "input": {"relation": "equivalent", "shared_subject": "Node", "difference": ""},
            "model": "test-model",
            "usage": {},
        }

    monkeypatch.setattr(pair_relation_module, "local_lane_call", fake_call)
    relation, fields = pair_relation("Node v26.5.1 was used", "Node v26.5.0 was used")
    assert relation == "conflicting"
    assert fields["vetoed_by"] == "numeric_signature"


def test_the_signature_leaves_a_true_paraphrase_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call(*_: Any, **__: Any) -> dict[str, Any]:
        return {
            "input": {"relation": "equivalent", "shared_subject": "orphans", "difference": ""},
            "model": "test-model",
            "usage": {},
        }

    monkeypatch.setattr(pair_relation_module, "local_lane_call", fake_call)
    relation, fields = pair_relation("38 orphans held 7.4 GB", "7.4 GB were held by 38 orphans")
    assert relation == "equivalent"
    assert "vetoed_by" not in fields


def test_a_cluster_needs_every_pair_not_a_path() -> None:
    """One mistaken edge must not merge two clusters through a shared member."""
    assert equivalence_clusters([(0, 1), (1, 2), (0, 2)]) == [(0, 1, 2)]
    assert equivalence_clusters([(0, 1), (1, 2)]) == [(0, 1)]
    assert equivalence_clusters([(0, 1), (2, 3), (3, 4), (2, 4)]) == [(0, 1), (2, 3, 4)]


def test_pairs_are_emitted_once_and_ordered_by_similarity() -> None:
    texts = ["alpha one", "alpha two", "beta one", "gamma one"]
    pairs = claim_pairs(texts, _Embedder(), 0.9, 3)
    assert pairs == [(0, 1, 1.0)]


def test_no_claims_means_no_pairs() -> None:
    assert claim_pairs([], _Embedder(), 0.75, 5) == []

"""Regression cases found during the independent context review."""

import pytest

from atrium.context.link_targets import link_targets
from atrium.context.matched_excerpt import matched_excerpt


@pytest.mark.parametrize(
    "stored,query",
    [
        ("cafe-au-lait", "café-au-lait"),
        ("café-au-lait", "cafe-au-lait"),
        ("cafe\u0301-au-lait", "café-au-lait"),
        ("ﬃ-café", "ffi-cafe"),
    ],
)
def test_folded_excerpt_retains_original_offsets(stored, query):
    text = "préfixe ﬃ " * 100 + stored + " trailing" * 100
    excerpt, start, end = matched_excerpt(text, query, 50)
    assert stored in excerpt
    assert start > 0
    assert excerpt == text[start:end]
    assert end - start <= 50


@pytest.mark.parametrize(
    "links",
    [
        "[[/etc/private]] " * 100,
        "[[https://example.test/x]] [[valid]] " * 100,
        "[[#anchor]] " * 100 + "[[valid]]",
    ],
    ids=["unsafe", "mixed", "anchors"],
)
def test_every_parsed_link_counts_toward_the_target_limit(links):
    targets = link_targets(links, "projects/access.md")
    assert len(targets) <= 50
    if links.startswith("[[#"):
        assert targets == []
    elif links.startswith("[[/etc"):
        assert targets == [()] * 50
    else:
        assert targets.count(()) == 25
        assert len(targets) == 50

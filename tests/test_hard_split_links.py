"""A positional cut never separates a link from its own brackets or target."""

from atrium.ingest.hard_split import hard_split
from atrium.ingest.max_chunk_chars import MAX_CHUNK_CHARS


def _straddling(link: str, inside: int) -> str:
    return "x" * (MAX_CHUNK_CHARS - inside) + link + " tail" * 50


def test_a_citation_and_its_anchor_stay_in_one_chunk():
    link = "[[S60]](#sources)"
    pieces = hard_split(_straddling(link, 7))
    assert any(link in piece for piece in pieces)


def test_a_wikilink_cut_inside_its_brackets_moves_whole():
    link = "[[topics/llm-wiki]]"
    pieces = hard_split(_straddling(link, 5))
    assert any(link in piece for piece in pieces)


def test_a_markdown_link_cut_inside_its_target_moves_whole():
    link = "[the runbook](projects/server-a/runbook.md)"
    pieces = hard_split(_straddling(link, 20))
    assert any(link in piece for piece in pieces)


def test_cutting_loses_nothing_and_keeps_the_bound():
    text = ("word [[S1]](#sources) " * 400) + "[[topics/llm-wiki]] " * 300
    pieces = hard_split(text)
    assert "".join(pieces) == text
    assert all(len(piece) <= MAX_CHUNK_CHARS for piece in pieces)


def test_a_link_longer_than_a_chunk_is_still_cut():
    text = "[[" + "a" * (MAX_CHUNK_CHARS * 2) + "]]"
    pieces = hard_split(text)
    assert "".join(pieces) == text
    assert all(len(piece) <= MAX_CHUNK_CHARS for piece in pieces)

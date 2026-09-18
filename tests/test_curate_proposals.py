"""Stage four: shortlist curated pages, place a claim, write a review sheet."""

import sqlite3
from pathlib import Path

import numpy as np

from atrium.curate.load_page_library import load_page_library
from atrium.curate.page_descriptor import page_descriptor
from atrium.curate.page_shortlist import page_shortlist
from atrium.curate.proposal_review import proposal_review


def test_a_page_descriptor_reads_a_folded_summary(tmp_path: Path) -> None:
    page = tmp_path / "brain" / "topics" / "retrieval.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\ntitle: Retrieval stack\nsummary:\n  'RAG against agentic search, and the\n"
        "  file-first baseline to beat first'\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert page_descriptor(tmp_path, "brain/topics/retrieval.md") == (
        "Retrieval stack -- RAG against agentic search, and the file-first baseline to beat first"
    )


def test_a_page_descriptor_falls_back_to_the_path(tmp_path: Path) -> None:
    assert page_descriptor(tmp_path, "brain/topics/missing.md") == "brain/topics/missing.md"


class _Embedder:
    def embed(self, texts: list[str]) -> np.ndarray:
        return np.zeros((len(texts), 2), dtype=np.float32)


def test_the_inbox_is_not_a_destination() -> None:
    """Unreviewed material is where claims come from, not a page they can join."""
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        "CREATE TABLE records (record_id TEXT, conversation_id TEXT, title TEXT,"
        " text TEXT, provider TEXT);"
        "CREATE TABLE vectors (record_id TEXT, vector BLOB);"
    )
    # A third page keeps the shared terms rare enough to score: a word every
    # chunk carries has zero inverse document frequency and ranks nothing.
    pages = [
        ("brain/inbox/raw-note.md", "pipelines merge claims into pages"),
        ("brain/topics/pipelines.md", "pipelines merge claims into pages"),
        ("brain/topics/unrelated.md", "invoices and quarterly taxes"),
    ]
    for record_id, (path, text) in enumerate(pages, 1):
        connection.execute(
            "INSERT INTO records (record_id, conversation_id, title, text, provider)"
            " VALUES (?, ?, ?, ?, 'brain')",
            (str(record_id), path, "Pipelines", text),
        )
    library = load_page_library(connection, _Embedder(), Path("/nowhere"))
    shortlist = page_shortlist(library, "pipelines merge claims into pages")
    assert [hit.path for hit in shortlist] == ["brain/topics/pipelines.md"]


def test_a_refusal_stays_in_the_review() -> None:
    """A claim with no home is evidence about the shortlist, not rubbish."""
    review = proposal_review(
        {
            "brain/topics/pipelines.md": [
                {
                    "text": "A claim.",
                    "why": "It is about pipelines.",
                    "first_seen": "2026-09-01",
                    "last_seen": "2026-09-02",
                    "episodes": 2,
                    "candidate_id": "abc",
                }
            ]
        },
        [{"text": "A file-level detail.", "shortlist": ["brain/topics/pipelines.md"]}],
    )
    assert "## brain/topics/pipelines.md" in review
    assert "Refused a destination" in review
    assert "A file-level detail." in review

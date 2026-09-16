"""What the Stop decision needs to know about a transcript, and nothing else."""

from dataclasses import dataclass

from atrium.session.transcript_boundary import TranscriptBoundary


@dataclass(frozen=True)
class TranscriptScan:
    """Metadata of a Claude Code transcript; never its text."""

    size: int
    entrypoint: str | None
    first_at: str | None
    boundary: TranscriptBoundary | None
    model: str | None
    prompts_after: int

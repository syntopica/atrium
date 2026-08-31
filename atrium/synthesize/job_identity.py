"""Derive the job key that makes one synthesis result skippable."""

import hashlib

from atrium.synthesize.segment_episodes import SEGMENTATION_FINGERPRINT
from atrium.synthesize.synthesis_prompt import PROMPT_SHA256
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION

GENERATOR_VERSION = "atrium-synthesize-2"


def job_identity(conversation_id: str, revision: str, episode_id: str, model_id: str) -> str:
    """Hash every input and recipe field except the output.

    Extracted so the re-key can recompute a key exactly as the synthesizer
    would. A second implementation of this formula would be a way for a
    migration to quietly orphan every record it touched.
    """
    payload = (
        f"{conversation_id}\x00{revision}\x00{episode_id}\x00{SEGMENTATION_FINGERPRINT}"
        f"\x00{model_id}\x00{PROMPT_SHA256}\x00{OUTPUT_SCHEMA_VERSION}\x00{GENERATOR_VERSION}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]

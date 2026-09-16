"""The registry key of one session record, independent of the batch recipe."""

import hashlib

from atrium.session.session_segmentation import SESSION_RECIPE_VERSION, SESSION_SEGMENTATION
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION


def session_job_identity(conversation_id: str, episode_id: str, model_id: str) -> str:
    """Hash every input and recipe field of a session record except the output.

    Deliberately not `job_identity`: that one folds in the batch prompt hash
    and the TextTiling fingerprint, so editing the batch prompt would have
    changed every session key and made every session record look unwritten.
    """
    payload = (
        f"{conversation_id}\x00{episode_id}\x00{model_id}\x00{SESSION_SEGMENTATION}"
        f"\x00{SESSION_RECIPE_VERSION}\x00{OUTPUT_SCHEMA_VERSION}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]

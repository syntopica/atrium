"""Session identities: the exporter's conversation id, a boundary-keyed episode."""

import hashlib

from atrium.session.session_conversation_id import session_conversation_id
from atrium.session.session_episode_identity import session_episode_identity
from atrium.session.session_job_identity import session_job_identity
from atrium.session.session_segmentation import SESSION_RECIPE_VERSION, SESSION_SEGMENTATION
from atrium.synthesize.synthesis_prompt import PROMPT_SHA256
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION


def test_conversation_id_is_the_exporters_formula():
    session = "a109ef39-701a-49f1-a709-346310fced31"
    expected = hashlib.sha256(f"claude-code\x00{session}".encode()).hexdigest()
    assert session_conversation_id("claude-code", session) == expected


def test_episode_id_is_stable_per_boundary_and_differs_across_boundaries():
    conversation = "c" * 64
    first = session_episode_identity(conversation, "uuid-1")
    assert first == session_episode_identity(conversation, "uuid-1")
    assert first != session_episode_identity(conversation, "uuid-2")
    assert len(first) == 24


def test_job_key_names_the_session_recipe_not_the_batch_prompt():
    conversation, episode, model = "c" * 64, "e" * 24, "session-claude"
    payload = (
        f"{conversation}\x00{episode}\x00{model}\x00{SESSION_SEGMENTATION}"
        f"\x00{SESSION_RECIPE_VERSION}\x00{OUTPUT_SCHEMA_VERSION}"
    )
    assert (
        session_job_identity(conversation, episode, model)
        == (hashlib.sha256(payload.encode()).hexdigest()[:32])
    )
    assert PROMPT_SHA256 not in payload

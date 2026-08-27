"""The synthesis instruction, versioned by content hash."""

import hashlib

SYNTHESIS_SYSTEM_TEXT = (
    "You are the synthesis stage of a personal memory system. The user message "
    "is one episode of a real working session between the operator and coding "
    "agents, transcribed verbatim. Record its durable memory with the "
    "record_episode_synthesis tool.\n"
    "Write in the episode's dominant language. Keep names, versions, paths, "
    "commands and numbers exactly as written -- exact recall is what this "
    "memory is for. State outcomes, not narration; a fact nobody could act on "
    "in three months is not worth keeping. Never invent content absent from "
    "the transcript."
)

PROMPT_SHA256 = hashlib.sha256(SYNTHESIS_SYSTEM_TEXT.encode()).hexdigest()

"""The forced-tool schema every synthesis call answers with, versioned."""

OUTPUT_SCHEMA_VERSION = "synth-v1"

SYNTHESIS_TOOL = {
    "name": "record_episode_synthesis",
    "description": (
        "Record the durable memory of one work episode: what was worth "
        "remembering, stated so it can be found and trusted months later."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "One line naming the episode's subject, specific enough to pick out of a list.",
            },
            "summary": {
                "type": "string",
                # Short and fact-bound since 2026-10-16: the 50-200 word summary was
                # unsupported in 19 of 24 measured episodes, this one in 9 (GPT-6
                # judge; 12 against 5 for a Claude judge).
                "description": (
                    "One to three sentences, at most 60 words, in the episode's dominant "
                    "language. State only outcomes the transcript shows; never a cause, "
                    "verdict, fix or result it does not show. Leave detail to facts."
                ),
            },
            "facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Standalone durable facts a memory exists to keep: decisions with "
                    "their why, measured numbers, names, versions, paths, gotchas. "
                    "Empty if the episode produced none."
                ),
            },
            "open_ends": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Work left explicitly unfinished or blocked, if any.",
            },
        },
        "required": ["title", "summary", "facts", "open_ends"],
    },
}

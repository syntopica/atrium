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
                "description": (
                    "What happened and what it means, 50-200 words, in the episode's "
                    "dominant language. Written for someone who was not there: no "
                    "unexplained codenames, concrete outcomes over narration."
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

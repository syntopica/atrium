"""Explicit trust classification shared by every agent-facing adapter."""


def trust_for_role(role: str) -> str:
    """Classify provenance without treating historical claims as current truth."""
    return {
        "note": "curated",
        "source": "untrusted",
        "user": "history",
        "assistant": "history",
        "episode": "synthesized",
        "synthesis": "synthesized",
    }.get(role, "unknown")

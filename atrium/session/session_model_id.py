"""The population name of records a session wrote with one model."""


def session_model_id(model: str) -> str:
    """Return ``session-<model>``; unknown models still get a population."""
    return f"session-{model or 'unknown'}"

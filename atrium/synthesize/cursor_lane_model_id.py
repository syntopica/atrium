"""The population name a cursor-lane run writes into every job key."""


def cursor_lane_model_id(model: str) -> str:
    """Name the population for ``model`` behind the Cursor transport.

    The transport is part of the name because Cursor's model list overlaps
    the other lanes' (``gemini-3.7-flash`` is served by agy too) while the
    CLI, its system prompt and its quota are not the same producer: the same
    episode through two transports is two jobs, never one record overwriting
    the other's paid-for output.
    """
    return f"cursor-{model}"

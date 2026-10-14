"""Say which path answered a context request and how long it took."""

from typing import Any

from atrium.context.elapsed_ms import elapsed_ms


def stamp_serving(result: dict[str, Any], served_by: str, started: float) -> dict[str, Any]:
    """Add ``served_by`` and the request's ``elapsed_ms`` to a context response.

    ``served_by`` is ``service`` (the resident service answered),
    ``service_timeout`` (it was listening but ran out of time) or
    ``in_process`` (no usable service, so this process retrieved). A slow
    prompt reads differently in each: a stalled service, or a cold scan.
    ``elapsed_ms`` is measured from the adapter's entry, so a caller timing
    the whole command sees its own start-up as the difference.
    """
    result["served_by"] = served_by
    result["elapsed_ms"] = elapsed_ms(started)
    return result

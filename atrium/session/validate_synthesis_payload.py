"""Accept exactly the four schema fields, typed, and nothing else."""

from typing import Any

from atrium.session.invalid_synthesis_error import InvalidSynthesisError

_LISTS = ("facts", "open_ends")
_TEXTS = ("title", "summary")


def validate_synthesis_payload(payload: Any) -> dict[str, Any]:
    """Return a clean copy holding only title, summary, facts and open_ends.

    An allowlist, not the schema's ``additionalProperties`` (which the
    synthesis schema leaves open): the record's metadata is the CLI's to
    write, and a stray key in the model's JSON must never reach it.
    """
    if not isinstance(payload, dict):
        raise InvalidSynthesisError("the payload must be one JSON object")
    unknown = sorted(set(payload) - set(_TEXTS) - set(_LISTS))
    if unknown:
        raise InvalidSynthesisError(f"unknown keys: {', '.join(unknown)}")
    clean: dict[str, Any] = {}
    for key in _TEXTS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidSynthesisError(f"{key} must be a non-empty string")
        clean[key] = value.strip()
    for key in _LISTS:
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidSynthesisError(f"{key} must be a list of strings")
        clean[key] = [item.strip() for item in value if item.strip()]
    return clean

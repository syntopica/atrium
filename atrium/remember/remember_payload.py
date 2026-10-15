"""Accept a remembered statement: the synthesis fields, facts and open ends optional."""

from typing import Any

from atrium.session.invalid_synthesis_error import InvalidSynthesisError
from atrium.session.validate_synthesis_payload import validate_synthesis_payload


def remember_payload(payload: Any) -> dict[str, Any]:
    """Return the clean four fields; a statement needs a title and a summary only.

    One decision is often one sentence, so the lists default to empty instead
    of being demanded, and the rest of the session contract applies unchanged.
    """
    if not isinstance(payload, dict):
        raise InvalidSynthesisError("the payload must be one JSON object")
    return validate_synthesis_payload({"facts": [], "open_ends": [], **payload})

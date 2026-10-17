"""Whether a user message is nothing but Codex's injected environment block."""

import re

_ENVIRONMENT_CONTEXT = re.compile(r"<environment_context>.*</environment_context>", re.DOTALL)


def is_environment_context(text: str) -> bool:
    """True only for the bare block: text a person adds after it keeps the message."""
    return _ENVIRONMENT_CONTEXT.fullmatch(text.strip()) is not None

"""The callable shape every synthesis lane implements."""

from collections.abc import Callable
from typing import Any, TypeAlias

# A producer is (system_text, user_text, tool) -> {"input", "model", "usage"},
# plus the deterministic model string that enters the job key. Two exist: the
# Max OAuth lane and the Codex CLI. Their records carry different recipe
# fingerprints and coexist in the registry without mixing.
Producer: TypeAlias = Callable[[str, str, dict[str, Any]], dict[str, Any]]

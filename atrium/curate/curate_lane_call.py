"""One curation model call, on the local lane or through the Codex CLI."""

from typing import Any

from atrium.synthesize.codex_lane_call import codex_lane_call
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import local_lane_call

CODEX = "codex"


def curate_lane_call(prompt: LanePrompt, tool: dict[str, Any], model: str) -> dict[str, Any]:
    """``codex`` (or ``codex:<model>``) uses the Codex CLI; any other name is an Ollama model.

    The curation stages ran only on the local model, which may not load while
    the owner uses the Mac; Codex answers the same contract with the account's
    default model at low effort unless one is named.
    """
    if model != CODEX and not model.startswith(f"{CODEX}:"):
        return local_lane_call(prompt, tool, model=model)
    user_text = (
        f"=== BEGIN {prompt.data_label} ===\n{prompt.user_text}\n=== END {prompt.data_label} ===\n\n"
        f"{prompt.instruction}"
    )
    named = model.partition(":")[2] or None
    return codex_lane_call(prompt.system_text, user_text, tool, model=named, effort="low")

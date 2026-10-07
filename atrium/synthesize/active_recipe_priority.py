"""Which synthesis population the index consumes when several coexist."""

import json
from pathlib import Path

# Recipe populations coexist in the registry (same episode synthesized by
# different producers under different job keys), but the index holds exactly
# one record per episode. This priority list decides which: first match wins.
# Codex first by operator directive (2026-08-28) -- it is the active producer;
# the Max-lane records remain as fallback for episodes codex has not covered.
_DEFAULT_PRIORITY = ["codex-cli-default", "claude-sonnet-5", "gemini-3.7-flash-medium"]


def active_recipe_priority(registry: Path) -> list[str]:
    """Return the model-priority list, creating the manifest on first use.

    The manifest is an explicit file rather than an inferred rule so a machine
    can change which population it serves without re-synthesizing anything,
    and so two machines serving different populations is a visible diff, not a
    silent divergence.
    """
    manifest = registry / "active-recipe.json"
    if manifest.exists():
        priority = json.loads(manifest.read_text()).get("model_priority")
        if isinstance(priority, list) and priority:
            return priority
    manifest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest.write_text(json.dumps({"model_priority": _DEFAULT_PRIORITY}, indent=1))
    return list(_DEFAULT_PRIORITY)

"""The active-recipe priority, read without ever writing the manifest."""

import json
from pathlib import Path

from atrium.synthesize.active_recipe import _DEFAULT_PRIORITY


def read_recipe_priority(registry: Path) -> list[str]:
    """Return the model-priority list a synthesis ingest would use, read-only.

    `active_recipe_priority` creates the manifest on first use, which is right
    for the ingest that consumes it and wrong for `status`: inspecting the
    system must never change which recipe the next ingest serves. A missing or
    malformed manifest answers with the same default the writer would create,
    without creating it.
    """
    manifest = registry / "active-recipe.json"
    if manifest.exists():
        try:
            priority = json.loads(manifest.read_text()).get("model_priority")
        except (json.JSONDecodeError, OSError):
            priority = None
        if isinstance(priority, list) and priority:
            return [str(model) for model in priority]
    return list(_DEFAULT_PRIORITY)

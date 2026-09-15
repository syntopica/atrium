"""Describe configuration resolution without silently hiding invalid metadata."""

import json
import os
from pathlib import Path
from typing import Any

from atrium.state.find_data_directory import find_data_directory
from atrium.state.state_directory import state_directory


def context_configuration(state: Path | None) -> dict[str, Any]:
    """Validate only configuration that participates in the selected instance."""
    selected = state_directory() if state is None else state
    result: dict[str, Any] = {"status": "explicit_state", "state": str(selected), "source": None}
    if os.environ.get("ATRIUM_STATE") or (
        state is not None and state.resolve() != state_directory().resolve()
    ):
        return result
    data = (
        Path(os.environ["SYNTOPICA_DATA"]).expanduser()
        if os.environ.get("SYNTOPICA_DATA")
        else find_data_directory(Path.cwd())
    )
    if data is None:
        result["status"] = "legacy_default"
        return result
    for name in ("syntopica.local.json", "syntopica.config.json"):
        path = data / name
        if not path.exists():
            continue
        result["source"] = str(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("configuration must be an object")
            section = value.get("atrium", {})
            if not isinstance(section, dict):
                raise ValueError("atrium must be an object")
            location = section.get("path")
            if location is not None and (not isinstance(location, str) or not location.strip()):
                raise ValueError("atrium.path must be a non-empty string")
        except (OSError, ValueError):
            result["status"] = "invalid"
            return result
        if location is not None:
            result["status"] = "configured"
            return result
    result["status"] = "default_path" if result["source"] else "missing"
    return result

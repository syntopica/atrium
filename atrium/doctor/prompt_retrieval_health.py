"""Whether Claude Code on this host still retrieves context before each prompt."""

import json
import os
from pathlib import Path

from atrium.doctor.finding import Finding
from atrium.doctor.has_prompt_retrieval import PLUGIN, has_prompt_retrieval


def prompt_retrieval_health(settings_files: list[Path] | None = None) -> Finding:
    """Warn when a Claude Code profile here has neither the plugin nor a prompt hook.

    From 2026-10-18 to 2026-11-06 a settings sync dropped the atrium-context
    plugin on both Macs and nothing retrieved per prompt; every index check
    stayed green because the index was fine. Hosts without Claude Code pass.
    """
    if settings_files is None:
        profiles = {Path.home() / ".claude"}
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            profiles.add(Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser())
        settings_files = sorted(profile / "settings.json" for profile in profiles)
    missing = []
    for path in settings_files:
        if not path.exists():
            continue
        try:
            settings = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            missing.append(str(path))
            continue
        if not has_prompt_retrieval(settings):
            missing.append(str(path))
    if missing:
        return Finding(
            check="prompt_hook",
            severity="warn",
            code="prompt_retrieval_missing",
            summary=f"no per-prompt retrieval in {', '.join(missing)}: enable {PLUGIN}",
            detail={"settings": missing},
        )
    return Finding(
        check="prompt_hook",
        severity="ok",
        code="prompt_retrieval_enabled",
        summary="every Claude Code profile here retrieves context before each prompt",
        detail={"settings": [str(path) for path in settings_files]},
    )

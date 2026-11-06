"""Whether one Claude Code settings document retrieves Atrium context on each prompt."""

from typing import Any

PLUGIN = "atrium-context@atrium"


def has_prompt_retrieval(settings: dict[str, Any]) -> bool:
    """True when the atrium-context plugin is enabled or a prompt hook calls atrium."""
    if (settings.get("enabledPlugins") or {}).get(PLUGIN) is True:
        return True
    for matcher in (settings.get("hooks") or {}).get("UserPromptSubmit") or []:
        for hook in matcher.get("hooks") or []:
            if "atrium" in str(hook.get("command", "")):
                return True
    return False

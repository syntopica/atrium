"""Extract explicit file operands from supported Codex tools."""

import re
import shlex
from pathlib import Path


def touched_paths(payload: dict) -> list[str]:
    """Return at most two project files; never execute or expand shell text."""
    arguments = payload.get("tool_input") or {}
    if not isinstance(arguments, dict):
        return []
    tool = payload.get("tool_name", "")
    candidates = []
    if tool in {"Read", "Edit", "Write"}:
        candidates = [arguments.get("file_path") or arguments.get("path") or ""]
    elif tool == "apply_patch":
        candidates = re.findall(
            r"^\*\*\* (?:Update|Add|Delete) File: (.+)$",
            arguments.get("command") or arguments.get("patch") or "",
            re.MULTILINE,
        )
    elif tool in {"Bash", "exec_command", "shell"}:
        command = arguments.get("command") or arguments.get("cmd") or ""
        if not isinstance(command, str) or any(character in command for character in ";|&`$\n<>"):
            return []
        try:
            words = shlex.split(command)
        except ValueError:
            return []
        if not words or words[0] not in {"cat", "head", "tail", "sed", "rg", "grep", "nl"}:
            return []
        candidates = [word for word in words[1:] if not word.startswith("-")]
    cwd = Path(payload.get("cwd") or ".").resolve()
    root = next((path for path in (cwd, *cwd.parents) if (path / ".git").exists()), None)
    if root is None:
        return []
    paths = []
    for candidate in candidates:
        if not candidate or "\x00" in candidate:
            continue
        path = (cwd / candidate).resolve()
        if path.is_relative_to(root) and path.is_file() and str(path) not in paths:
            paths.append(str(path))
    return paths[:2]

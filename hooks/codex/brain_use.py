"""Tell the person, at the end of each Codex turn, how the turn used the brain.

Codex has no footer a hook can draw in, so the account is the Stop hook's
`systemMessage`: `atrium · brain: 1 cited, 2 read, 1 lookup`. It counts what is
observable, which is not the same as what was injected: the atrium tools and
CLI the model called (PostToolUse), the instance's notes it opened from the
shell, and the note paths its final answer names (the evidence block asks for
the path of each note an answer relies on). A turn that used nothing says
nothing, since Codex draws every `systemMessage` as a warning.

One script for three events, keyed on `hook_event_name`; the turn's tally is a
small file per session and turn under the temporary directory, changed under a
lock and replaced atomically, since parallel tool calls finish together, and
removed by Stop. A lookup counts as read only the notes its result returned as
evidence (`note_path`), not every path quoted in it. Codex's hook protocol is the one this
reads (https://learn.chatgpt.com/docs/hooks); Claude Code gets the same account
from the `atrium-context` mod instead.
"""

import contextlib
import fcntl
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_NOTE_PATH = re.compile(r"\bbrain/[A-Za-z0-9._/-]+\.md\b")
_EVIDENCE_NOTE = re.compile(r'note_path\\?"\s*:\s*\\?"(brain/[A-Za-z0-9._/-]+\.md)')
_ATRIUM_TOOL = re.compile(r"^mcp__(plugin_.+_)?atrium__")
_ATRIUM_COMMAND = re.compile(r"\b(atrium\s+(context|search|recall)|brain\s+query)\b")
_SHELL_TOOLS = frozenset({"Bash", "exec_command", "shell"})
# A shell command that reads a file's content; a path merely printed or listed
# by any other command is not a note read.
_READ_COMMAND = re.compile(r"(^|[\s;|&(])(cat|sed|head|tail|less|more|bat|nl|awk|grep|rg)\s")
_EMPTY = {"lookups": 0, "read": []}


def _tally_path(payload: dict) -> Path:
    key = f"{payload.get('session_id') or ''}-{payload.get('turn_id') or ''}"
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", key)
    return Path(tempfile.gettempdir()) / "atrium-brain-use" / f"{safe}.json"


@contextlib.contextmanager
def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / ".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _load(path: Path) -> dict:
    try:
        return {**_EMPTY, **json.loads(path.read_text())}
    except (OSError, ValueError):
        return dict(_EMPTY)


def _save(path: Path, tally: dict) -> None:
    staged = path.with_suffix(f".{os.getpid()}.tmp")
    staged.write_text(json.dumps(tally))
    staged.replace(path)


def _safe(path: str) -> bool:
    return all(part not in {"", ".", ".."} for part in path.split("/"))


def _note_paths(text: str, pattern: re.Pattern[str] = _NOTE_PATH) -> list[str]:
    return [path for path in dict.fromkeys(pattern.findall(text)) if _safe(path)]


def _instance_notes(command: str) -> list[str]:
    """The instance's notes a reading shell command names by their full path."""
    data = os.environ.get("SYNTOPICA_DATA", "").rstrip("/")
    if not data or not _READ_COMMAND.search(command):
        return []
    return _note_paths(
        command, re.compile(re.escape(data + "/") + r"(brain/[A-Za-z0-9._/-]+\.md)\b")
    )


def _access(payload: dict) -> tuple[int, list[str]] | None:
    """Lookups and notes one finished tool call took from the brain, or None."""
    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") if isinstance(tool_input, dict) else ""
    command = " ".join(command) if isinstance(command, list) else str(command or "")
    response = json.dumps(payload.get("tool_response"))
    if _ATRIUM_TOOL.match(tool) or (tool in _SHELL_TOOLS and _ATRIUM_COMMAND.search(command)):
        return 1, _note_paths(response, _EVIDENCE_NOTE)
    if tool in _SHELL_TOOLS:
        notes = _instance_notes(command)
        return (0, notes) if notes else None
    return None


def _notice(tally: dict, cited: list[str]) -> str:
    parts = []
    if cited:
        parts.append(f"{len(cited)} cited")
    if tally["read"]:
        parts.append(f"{len(tally['read'])} read")
    if tally["lookups"]:
        parts.append(f"{tally['lookups']} lookup" + ("s" if tally["lookups"] > 1 else ""))
    return "atrium · brain: " + ", ".join(parts) if parts else ""


def main() -> int:
    """Add to or report the turn's tally; never block anything."""
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    event = payload.get("hook_event_name")
    path = _tally_path(payload)
    access = _access(payload) if event == "PostToolUse" else None
    if access:
        with _locked(path):
            tally = _load(path)
            tally["lookups"] += access[0]
            tally["read"] = list(dict.fromkeys([*tally["read"], *access[1]]))
            _save(path, tally)
    elif event == "Stop":
        with _locked(path):
            tally = _load(path)
            with contextlib.suppress(OSError):
                path.unlink()
        notice = _notice(tally, _note_paths(payload.get("last_assistant_message") or ""))
        if notice:
            json.dump({"systemMessage": notice}, sys.stdout)
    return 0


if __name__ == "__main__":
    with contextlib.suppress(Exception):
        sys.exit(main())
    sys.exit(0)

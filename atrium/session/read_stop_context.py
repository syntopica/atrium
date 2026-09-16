"""Resolve a Stop payload into a context, or None for an excluded session."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from atrium.session.is_scratch_path import is_scratch_path
from atrium.session.read_session_state import read_session_state
from atrium.session.scan_transcript import scan_transcript
from atrium.session.session_state_path import session_state_path
from atrium.session.stop_context import StopContext


def read_stop_context(payload: dict[str, Any], environ: Mapping[str, str]) -> StopContext | None:
    """None when the session is opted out, scratch, a subagent, headless or gone.

    `entrypoint` is `cli` for interactive sessions and `sdk-py` for SDK runs;
    a plain `claude -p` is not distinguishable by it and is caught by the
    scratch rule where this repository's tooling runs it.
    """
    session_id = str(payload.get("session_id") or "")
    transcript = Path(str(payload.get("transcript_path") or ""))
    cwd = str(payload.get("cwd") or "")
    tmpdir = environ.get("TMPDIR")
    if (
        not session_id
        or environ.get("ATRIUM_NO_SESSION_RECORD")
        or payload.get("agent_id")
        or is_scratch_path(cwd, tmpdir)
        or is_scratch_path(str(transcript), tmpdir)
        or not transcript.is_file()
    ):
        return None
    state_path = session_state_path(session_id, environ)
    state = read_session_state(state_path)
    consumed = state.get("consumed") if isinstance(state.get("consumed"), dict) else None
    scan = scan_transcript(transcript, int(consumed["offset"]) if consumed else 0)
    if scan.entrypoint != "cli":
        return None
    return StopContext(session_id, transcript, cwd, state_path, state, consumed, scan)

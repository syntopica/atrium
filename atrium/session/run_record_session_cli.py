"""The `atrium record-session` command: synthesis JSON in, receipt out."""

import os
import sys
from pathlib import Path

from atrium.session.record_session import record_session


def run_record_session_cli(checkpoint_id: str, registry: Path, *, nothing_durable: bool) -> int:
    """Read the payload from stdin unless ``--nothing-durable``; report one line."""
    payload_text = "" if nothing_durable else sys.stdin.read()
    outcome = record_session(
        checkpoint_id, payload_text, registry, os.environ, nothing_durable=nothing_durable
    )
    if outcome.stdout:
        print(outcome.stdout)
    if outcome.stderr:
        print(f"atrium record-session: {outcome.stderr}", file=sys.stderr)
    return outcome.status

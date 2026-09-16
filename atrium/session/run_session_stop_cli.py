"""The `atrium session-stop` command: hook payload in, refusal or nothing out."""

import json
import os
import sys

from atrium.session.session_stop_decision import session_stop_decision


def run_session_stop_cli() -> int:
    """Always exit 0: a broken hook must cost the feature, never the session."""
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        decision = session_stop_decision(payload, os.environ)
    except (OSError, ValueError) as error:
        print(f"atrium session-stop: {error}", file=sys.stderr)
        return 0
    if decision:
        print(json.dumps(decision, ensure_ascii=False))
    return 0

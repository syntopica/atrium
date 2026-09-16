"""Run the Cursor CLI in its own process group and take the group down after."""

import contextlib
import os
import signal
import subprocess


def run_cursor_in_own_session(
    argv: list[str], prompt: str, cwd: str, timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run ``argv`` with ``prompt`` on stdin and kill its whole group afterwards.

    `cursor-agent` spawns an `index.js worker-server` that outlives the CLI:
    measured 2026-09-16, one hour of the drip left 38 orphaned worker-servers
    (parent pid 1) holding 7.4 GB, and free memory fell from 67% to 46%. A
    fresh session makes the child's pid its group id, so everything the CLI
    started is reachable by one killpg once the answer is in hand, and a
    timeout takes the whole group down instead of the wrapper alone.
    """
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(prompt, timeout=timeout)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

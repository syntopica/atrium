"""Bound runtime and stop the process group if its progress log stalls."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    """Watch only the child group launched here, with a 120-second stall limit."""
    log = Path(sys.argv[1])
    started = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as handle:
        process = subprocess.Popen(
            sys.argv[2:], stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
        )
        print(f"supervising pid={process.pid} log={log} stall=120s total=1800s", flush=True)
        while process.poll() is None:
            if time.time() - log.stat().st_mtime > 120 or time.monotonic() - started > 1800:  # noqa: PLR2004 -- explicit guard limits
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise SystemExit("benchmark stopped at its stall or total-runtime limit")
            time.sleep(5)
    raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()

"""Run the packaged Codex usage hook through its legacy entry point."""

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins/atrium-codex/hooks"))
runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "plugins/atrium-codex/hooks/brain_use.py"),
    run_name="__main__",
)

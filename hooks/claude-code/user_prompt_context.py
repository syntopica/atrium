"""Run the shared prompt hook through its legacy entry point."""

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "plugins/atrium-codex/hooks/user_prompt_context.py"),
    run_name="__main__",
)

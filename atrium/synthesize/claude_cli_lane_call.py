"""One structured synthesis call through the Claude Code CLI's subscription."""

import subprocess
import tempfile
from typing import Any

from atrium.synthesize.claude_cli_command import claude_cli_command
from atrium.synthesize.claude_cli_failure import claude_cli_failure
from atrium.synthesize.claude_stream_result import claude_stream_result
from atrium.synthesize.claude_stream_utilization import claude_stream_utilization


def claude_cli_lane_call(
    system_text: str, user_text: str, tool: dict[str, Any], model: str
) -> dict[str, Any]:
    """Return {"input", "model", "usage", "utilization"} from one `claude -p` run.

    The transcript goes over stdin and the answer is read from the result's
    ``structured_output``, never scraped from free text. ``utilization`` is the
    fullest usage window the run reported, or ``None``. The CLI runs in an empty
    scratch directory so no project instructions are discovered.
    """
    prompt = (
        "Answer ONLY with the JSON object the enforced output schema describes. "
        f"The episode transcript follows.\n\n{user_text}"
    )
    with tempfile.TemporaryDirectory(prefix="atrium-claude-") as scratch:
        completed = subprocess.run(  # noqa: PLW1510 -- returncode handled below
            claude_cli_command(system_text, tool["input_schema"], model),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=1200,
            cwd=scratch,
        )
    result = claude_stream_result(completed.stdout)
    output = result.get("structured_output")
    if completed.returncode != 0 or result.get("is_error") or not isinstance(output, dict):
        streams = f"{completed.stderr}\n{result.get('result') or completed.stdout}"
        raise claude_cli_failure(completed.returncode, streams, result.get("api_error_status"))
    missing = [key for key in tool["input_schema"]["required"] if key not in output]
    if missing:
        raise RuntimeError(f"claude output missing required keys: {missing}")
    resolved = next(iter(result.get("modelUsage") or {}), model)
    return {
        "input": output,
        "model": resolved,
        "usage": result.get("usage") or {},
        "utilization": claude_stream_utilization(completed.stdout),
    }

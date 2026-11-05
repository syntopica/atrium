"""One structured synthesis call through the Claude Code CLI's subscription."""

import json
import subprocess
import tempfile
from typing import Any

from atrium.synthesize.claude_cli_command import claude_cli_command
from atrium.synthesize.claude_cli_failure import claude_cli_failure


def claude_cli_lane_call(
    system_text: str, user_text: str, tool: dict[str, Any], model: str
) -> dict[str, Any]:
    """Return {"input": ..., "model": ..., "usage": ...} from one `claude -p` run.

    The transcript goes over stdin and the answer is read from the result's
    ``structured_output``, never scraped from free text. The CLI runs in an empty
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
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {}
    output = result.get("structured_output")
    if completed.returncode != 0 or result.get("is_error") or not isinstance(output, dict):
        streams = f"{completed.stderr}\n{result.get('result') or completed.stdout}"
        raise claude_cli_failure(completed.returncode, streams, result.get("api_error_status"))
    missing = [key for key in tool["input_schema"]["required"] if key not in output]
    if missing:
        raise RuntimeError(f"claude output missing required keys: {missing}")
    resolved = next(iter(result.get("modelUsage") or {}), model)
    return {"input": output, "model": resolved, "usage": result.get("usage") or {}}

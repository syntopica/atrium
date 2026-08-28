"""One structured synthesis call through the Codex CLI's own quota."""

import json
import re
import subprocess
import tempfile
from pathlib import Path

# The job key needs a deterministic model string BEFORE the call; the account
# default is what actually runs, and the resolved id is recorded per record.
CODEX_MODEL_ID = "codex-cli-default"

_MODEL_LINE = re.compile(r"^model:\s*(\S+)", re.MULTILINE)
_TOKENS_LINE = re.compile(r"^tokens used\s*\n(\d+)", re.MULTILINE)


def codex_lane_call(system_text: str, user_text: str, tool: dict) -> dict:
    """Return {"input": ..., "model": ..., "usage": ...} from one codex exec run.

    Read-only sandbox, prompt over stdin (transcripts exceed argv comfort),
    response shape pinned with --output-schema and read back from the
    last-message file -- never scraped out of the event stream.
    """
    with tempfile.TemporaryDirectory(prefix="atrium-codex-") as scratch:
        schema_path = Path(scratch) / "schema.json"
        output_path = Path(scratch) / "last-message.json"
        # OpenAI's strict output mode refuses any object schema that does not
        # pin additionalProperties: false; the shared tool schema stays
        # untouched (Anthropic neither needs nor stores that key).
        schema = {**tool["input_schema"], "additionalProperties": False}
        schema_path.write_text(json.dumps(schema))
        prompt = (
            f"{system_text}\n\nAnswer ONLY with the JSON object the enforced "
            f"output schema describes. The episode transcript follows.\n\n{user_text}"
        )
        completed = subprocess.run(  # noqa: PLW1510 -- returncode handled below
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "-C",
                scratch,
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
                "-",
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        if completed.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                f"codex exec failed ({completed.returncode}): "
                f"{(completed.stderr or completed.stdout)[-400:]}"
            )
        output = json.loads(output_path.read_text())
        missing = [key for key in tool["input_schema"]["required"] if key not in output]
        if missing:
            raise RuntimeError(f"codex output missing required keys: {missing}")
        streams = f"{completed.stdout}\n{completed.stderr}"
        model = _MODEL_LINE.search(streams)
        tokens = _TOKENS_LINE.search(streams)
        return {
            "input": output,
            "model": model.group(1) if model else "codex-cli-default",
            "usage": {"total_tokens": int(tokens.group(1))} if tokens else {},
        }

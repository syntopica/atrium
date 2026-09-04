"""One structured synthesis call through the Codex CLI's own quota."""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError

# The job key needs a deterministic model string BEFORE the call; the account
# default is what actually runs, and the resolved id is recorded per record.
CODEX_MODEL_ID = "codex-cli-default"

_MODEL_LINE = re.compile(r"^model:\s*(\S+)", re.MULTILINE)
_TOKENS_LINE = re.compile(r"^tokens used\s*\n(\d+)", re.MULTILINE)


def codex_lane_call(
    system_text: str,
    user_text: str,
    tool: dict[str, Any],
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    """Return {"input": ..., "model": ..., "usage": ...} from one codex exec run.

    Read-only sandbox, prompt over stdin (transcripts exceed argv comfort),
    response shape pinned with --output-schema and read back from the
    last-message file -- never scraped out of the event stream.

    ``model`` and ``effort`` override the account default. Synthesis is
    extraction, not judgement, so the account's reasoning effort is the wrong
    price for it; whatever is chosen must also enter the job key, which is why
    the caller passes the same pair to ``codex_lane_model_id``.
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
        selection: list[str] = []
        if model:
            selection += ["-m", model]
        if effort:
            selection += ["-c", f"model_reasoning_effort={effort}"]
        completed = subprocess.run(  # noqa: PLW1510 -- returncode handled below
            [
                "codex",
                "exec",
                "--skip-git-repo-check",
                *selection,
                # Synthesis is pure text-to-JSON: no MCP server is needed, and
                # serena is `required = true` in the user config -- under
                # parallel workers its per-session startup times out and kills
                # session creation (179 conversations failed that way before
                # this flag).
                "-c",
                "mcp_servers.serena.enabled=false",
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
            # A spent usage window cannot succeed until its reset. Raising the
            # quota error lets the pass stop at the wall instead of grinding
            # 43,000 conversations into "FAILED" lines, which is what the agy
            # lane did for eighteen hours before it learned the same thing.
            streams_lower = f"{completed.stderr}\n{completed.stdout}".lower()
            if "usage limit" in streams_lower or "quota" in streams_lower:
                raise QuotaExhaustedError((completed.stderr or completed.stdout).strip()[-400:])
            raise RuntimeError(
                f"codex exec failed ({completed.returncode}): "
                f"{(completed.stderr or completed.stdout)[-400:]}"
            )
        output = json.loads(output_path.read_text())
        missing = [key for key in tool["input_schema"]["required"] if key not in output]
        if missing:
            raise RuntimeError(f"codex output missing required keys: {missing}")
        streams = f"{completed.stdout}\n{completed.stderr}"
        resolved = _MODEL_LINE.search(streams)
        tokens = _TOKENS_LINE.search(streams)
        return {
            "input": output,
            # What actually ran, recorded per record: the requested model is in
            # the job key, the resolved one is evidence of what answered.
            "model": resolved.group(1) if resolved else (model or CODEX_MODEL_ID),
            "usage": {"total_tokens": int(tokens.group(1))} if tokens else {},
        }

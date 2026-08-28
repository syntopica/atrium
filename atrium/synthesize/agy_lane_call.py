"""One structured synthesis call through agy's Gemini bulk quota."""

import json
import re
import subprocess

# The brain's routing rule: whole-corpus bulk goes to Gemini via agy -- its
# quota is the one that survives it. Newest Flash at medium effort; synthesis
# is extraction, not judgement, which is the one place the measured comparison
# preferred Pro.
AGY_MODEL_ID = "gemini-3.7-flash-medium"

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def agy_lane_call(system_text: str, user_text: str, tool: dict) -> dict:
    """Return {"input": ..., "model": ..., "usage": ...} from one agy print run.

    Gemini prompting inverts the usual order: the transcript goes FIRST and
    the instructions last, anchored to it -- instructions ahead of a large
    context get diluted. Plan mode plus disabled slash expansion because the
    prompt inlines captured conversation text (the brain's standing rule for
    read-only passes over untrusted inline content).
    """
    schema = {**tool["input_schema"], "additionalProperties": False}
    prompt = (
        f"EPISODE TRANSCRIPT:\n{user_text}\n\n---\n\n"
        f"{system_text}\n\n"
        "Based entirely on the transcript above, using no outside knowledge, "
        "answer with ONE JSON object matching this schema and nothing else -- "
        "no prose, no code fence:\n"
        f"{json.dumps(schema)}"
    )
    # agy does not read the prompt from stdin: it must be attached to the
    # flag itself (`--print='...'`). Episodes are ceiling-bounded well under
    # ARG_MAX, but guard anyway rather than fail with an opaque E2BIG.
    if len(prompt) > 700_000:
        raise RuntimeError(f"prompt too large for argv ({len(prompt)} chars)")
    completed = subprocess.run(  # noqa: PLW1510 -- returncode handled below
        [
            "agy",
            f"--print={prompt}",
            "--model",
            AGY_MODEL_ID,
            "--mode",
            "plan",
            "--disable-slash-commands",
            "--print-timeout",
            "10m",
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"agy failed ({completed.returncode}): {(completed.stderr or completed.stdout)[-300:]}"
        )
    match = _JSON_BLOCK.search(completed.stdout)
    if match is None:
        raise RuntimeError(f"agy returned no JSON object: {completed.stdout[-300:]!r}")
    output = json.loads(match.group(0))
    missing = [key for key in tool["input_schema"]["required"] if key not in output]
    if missing:
        raise RuntimeError(f"agy output missing required keys: {missing}")
    return {"input": output, "model": AGY_MODEL_ID, "usage": {}}

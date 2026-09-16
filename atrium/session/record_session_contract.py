"""What `atrium record-session` expects on stdin: the contract, for `--help`."""

import json

from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL

RECORD_SESSION_CONTRACT = (
    "Write the running session's own memory record for the checkpoint the Stop hook "
    "froze. Stdin is ONE JSON object with exactly these keys:\n\n"
    + json.dumps(SYNTHESIS_TOOL["input_schema"], ensure_ascii=False, indent=1)
    + "\n\nWrite in the episode's dominant language. Keep names, versions, paths, commands "
    "and numbers exactly as they appeared; state outcomes, not narration; put decisions "
    "with their why and measured numbers in facts; put what was left unfinished or "
    "blocked in open_ends; never invent content absent from the session. Secrets are "
    "redacted before the write and the accepted record is printed back. Exit 2 names the "
    "invalid field so the JSON can be fixed and sent again; exit 3 means the checkpoint is "
    "not pending (already consumed, boundary gone, or recording disabled)."
)

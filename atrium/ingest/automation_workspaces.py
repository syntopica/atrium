"""The temporary directories the pipeline's own codex runs work in."""

# Each pattern is one creator, found in its source; a person can work from a
# temporary directory too, so `/T/` alone is no evidence of automation, and a
# prefix whose creator is unknown stays indexed.
AUTOMATION_WORKSPACES = (
    # atrium `codex_lane_call`: one synthesis job per directory; 43,085 archived
    # conversations by 2026-10-11 whose user turns are Atrium's own prompts.
    r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/atrium-codex-[^/]+/?$",
    # clips `create-ingest-worktree.ts`: `brain-ingest-*/<clip ULID>`, a clip
    # synthesized into the brain; the note it writes is indexed on its own.
    r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/brain-ingest-[^/]+/[0-9A-HJKMNP-TV-Z]{26}/?$",
    # worker `run_task.py`: `worker-task-*/workspace`, a queued batch task.
    r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/worker-task-[^/]+/workspace/?$",
    # clips `run-codex-triage-batch.ts`: newsletter titles triaged in batches.
    # Exactly mkdtemp's six-character suffix, so the agy runner's
    # `clips-triage-agy-*` is not claimed by this creator.
    r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/clips-triage-[A-Za-z0-9]{6}/?$",
    # The 2026-09-01 synthesis model bench (Claude session `adfb9b599d27`), a
    # one-off script outside any repository: candidate models ran on real
    # episodes in `bench-*`, a blind judge scored them in `judge-*`. Python's
    # TemporaryDirectory suffix is exactly eight characters.
    r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/(?:bench|judge)-[a-z0-9_]{8}/?$",
)

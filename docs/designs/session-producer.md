# The session producer: the agent that lived the episode records it

Status: revision 2, 2026-09-16, after one adversarial review round (Codex,
17 findings; the ones that changed the design are named inline). Implemented
from this revision.

## Why

Every synthesis record so far is written by a cold reader: a batch lane (agy,
cursor, codex, max) reads a transcript it was not part of and infers what
mattered. Measured on 2026-09-16 over the 3,165 records the drip wrote that
day:

- 7 of the first 8 cursor failures were the reader performing the transcript's
  task (a security review) instead of summarizing it; fixed by prompt order,
  but the failure mode is structural: the reader does not know the intent.
- 111 records (1 in 28) have no facts and titles like "Structured output
  provided successfully": the tail of a subagent session cut into an episode
  of its own by blind segmentation, each costing a full call (35k input
  tokens on the cursor lane).
- The batch lanes need quota the operator does not have to spare: the Codex
  account is reserved, agy walls after ~450-800 records per 5-hour window,
  cursor is the fallback. A person with one subscription has no batch lane
  at all.

The agent that did the work knows why it did it, where the episode boundaries
are, and what was left open. It is already running on the account the person
pays for. memstore put the memory write in the session for this reason and
got three things wrong that this design must not repeat: writes that depend
on a daemon and are dropped silently without it (two days lost, 2026-07-29),
headless `claude -p` runs feeding their own curation back in as conversations
(771 junk drawers pruned 2026-08-05), and a curation step the session was
merely asked to do in CLAUDE.md, which it skipped.

## What

A fifth producer, `session`, whose records enter the same registry as every
other population, are served by the same active-recipe priority, and are
indexed by the same `ingest-synthesis`.

Three parts, all in this repository:

1. `atrium session-stop`: the decision behind the Claude Code `Stop` hook.
   Reads the hook payload, decides whether the session owes a record, and if
   so freezes a checkpoint and prints the refusal that makes the model write
   one. The shell hook is a two-line adapter around it.
2. `atrium record-session`: turns one JSON synthesis into a registry record
   for a frozen checkpoint. The model contributes the JSON; the CLI does
   every deterministic thing (identity, validation, redaction, dedup, write).
3. A backfill rule: the batch lanes skip a conversation that has session
   records, so nothing is paid for twice.

Recall on session start already exists (`~/.claude/hooks/atrium-recall.sh`)
and does not change.

## Identity

The archive derives a conversation's id as `sha256("claude-code\0" +
session_id)` (`scripts/lib/conversations/streamJsonlConversationRecord.ts`
in rocket-agents), and Claude Code hands the hook `session_id`. The session
therefore knows its archive conversation id before the conversation is
archived, and its records join the archived conversation's with no rekey.

A session episode is identified by its boundary in the transcript, never by
archive events it cannot see:

    SESSION_SEGMENTATION = "session-self-v1"
    episode_id = sha256(SESSION_SEGMENTATION \0 conversation_id \0 boundary_uuid)[:24]

`boundary_uuid` is the `uuid` of the last eligible transcript record (a
`user` or `assistant` record carrying `uuid` and `timestamp`) **at the moment
the hook froze the checkpoint**, not when the record is written (review
finding 3: the recording tool call itself appends records; freezing first
keeps the bookkeeping out of the episode and makes a retry hit the same
boundary).

The job key is session-specific (finding 12: `job_identity` folds in the
batch prompt hash and cutter fingerprint, so a batch prompt edit would have
changed every session key):

    job_key = sha256(conversation_id \0 episode_id \0 model_id \0 SESSION_SEGMENTATION
                     \0 SESSION_RECIPE_VERSION \0 OUTPUT_SCHEMA_VERSION)[:32]

with `model_id = "session-" + model` and `model` the last assistant record's
`message.model` at the boundary. `SESSION_RECIPE_VERSION` names the
instruction text the hook gives the model; editing that text bumps it.

The re-key (`rekey_synthesis_record`, `rekey_synthesis_registry`) returns a
record whose `segmentation` is `session-self-v1` unchanged: it has no event
ids to re-qualify, and today it would crash on the empty list.

## The record

Same fields as a batch record, with `event_ids` empty, `map_chunks` 0,
`revision_sha256` empty, `usage` zeros, `authored_at` the boundary timestamp,
`segmentation` `session-self-v1`, plus:

- `workspace`: `project_workspace(cwd)`, the `[HOME]`-redacted project root
  the recall query asks for (finding 8: the raw cwd matches nothing).
  `ingest-synthesis` uses the archive's workspace when the conversation is
  archived and this field otherwise, both through `canonical_workspace`.
- `session`: `{"since": ISO, "until": ISO, "boundary_uuid", "boundary_line"}`,
  timestamps normalized to UTC milliseconds the way the exporter writes them.
  Informational in this revision; no logic compares them (finding 4, 5, 6:
  a timestamp cutoff against TextTiling episodes is neither exact nor
  aligned, so the backfill rule below works at conversation level instead).

Every string in `output` passes through the archive's redaction policy,
ported to `redact_sensitive_text` (private key blocks, assigned secrets,
bearer/AWS/GitHub/OpenAI/Slack tokens, URL credentials) before it is written
(finding 1: this route bypassed the exporter's redaction). The accepted
record is printed to stdout on success, so the tool result carries it into
the transcript and the archive: the judgment is captured in layer 1 and can
be replayed if the registry is lost (finding 2: a Bash command's `input.command`
is not exported text; a tool result is).

## The checkpoint

State lives under the instance: `state_directory() / "session-record" /
<sha256(session_id)[:16]>.json` (finding 14, 15: the filename never comes
from input; two instances never share a file). One JSON per session:

    {"session_id", "transcript_path", "cwd", "workspace",
     "pending": {"id", "boundary_uuid", "boundary_line", "boundary_offset",
                 "boundary_at", "since", "model", "attempts"} | null,
     "consumed": {"offset", "at", "job_key" | null} | null}

`pending.id` = `sha256(session_id \0 boundary_uuid)[:16]`; it is the only
thing the model is told, and the only argument `record-session` takes. The
CLI resolves everything else from the checkpoint, so the model cannot pick a
session, a transcript, a path or an identity. Writes are atomic
(temporary file, rename).

## `atrium session-stop`

Stdin: the hook payload. Stdout: `{"decision": "block", "reason": ...,
"systemMessage": ..., "suppressOutput": true}` or nothing. `reason` is the
instruction the model acts on; `systemMessage` is the one line Claude Code
renders for the person ("atrium: recording this session's memory record since
10:21 UTC (checkpoint ...)"), because the terminal otherwise prints the whole
reason as "Stop hook error". `suppressOutput` keeps the JSON out of the
transcript view. Always exit 0: a broken hook must cost the feature, never the
session. Order of checks:

1. Silent when `ATRIUM_NO_SESSION_RECORD` is set; when `cwd` or the
   transcript path is under a scratch root (`/private/tmp`, `/tmp`, `$TMPDIR`,
   or the encoded `-private-tmp`, `-tmp`, `-var-folders` prefixes); when the
   payload carries `agent_id`; when the transcript is missing.
2. Scan the transcript: `entrypoint` of the first record, size, the last
   eligible record (uuid, timestamp, line, byte offset), the last assistant
   model, and, from the consumed offset onward, whether a `user` prompt
   exists. Silent when `entrypoint` is not `cli` (SDK runs write `sdk-py`;
   a plain `claude -p` is indistinguishable by this field and is caught by
   the scratch-root rule where this repository's tooling runs it, finding 13).
3. If `stop_hook_active` is true (the turn after a refusal): if the pending
   checkpoint was consumed, silent. If not, and `attempts < 3`, refuse again
   with the same checkpoint id and a note that the previous turn did not
   record it (finding 10: one ignored instruction must not count as
   completion). At the third miss, stay silent; the checkpoint stays pending
   and the next ordinary turn re-issues it.
4. A pending checkpoint whose boundary uuid still exists in the transcript is
   re-issued as is. One whose uuid is gone (transcript replaced, `/clear`,
   resumed elsewhere) is dropped: that interval is uncovered, and says so in
   nothing but the log (finding 11: no claim of coverage it cannot prove).
5. Baseline = the consumed checkpoint's offset and time, else the transcript's
   first record. Silent unless at least one `user` prompt arrived after the
   baseline (finding 13: the recording bookkeeping must not trigger the next
   reminder). Then refuse when `new_bytes >= 32 KiB`, or when `new_bytes >=
   4 KiB` and `now - baseline_at >= 1800 s`. These are reminder limits, not
   episode semantics (finding 9): a session that ends under them is left to
   the batch lanes, which is exactly what those lanes are for, and is stated
   as the residual loss below.
6. Freeze the checkpoint, then print the refusal.

The refusal text is three sentences, because Claude Code prints it whole in
the terminal as "Stop hook error: ..." (seen on the first live refusal,
2026-09-16 12:0x): record the episode since `<since>` by running

    atrium record-session --checkpoint <id> <<'JSON'
    {"title": ..., "summary": ..., "facts": [...], "open_ends": [...]}
    JSON

the four keys in one line, the rules in one sentence (the full schema and
rules are `atrium record-session --help`), that is, the rules the batch prompt already states (the
episode's dominant language; names, versions, paths, commands and numbers
exactly as they appeared; outcomes not narration; `open_ends` for what was
left unfinished; nothing invented); `--nothing-durable` when the interval
produced nothing worth keeping (finding 9); then stop, no other work.

## `atrium record-session --checkpoint ID [--nothing-durable]`

Stdin: the synthesis JSON. Resolves the checkpoint (exit 3 when no session
state holds a pending checkpoint with that id, when the boundary uuid is no
longer in the transcript, or when `ATRIUM_NO_SESSION_RECORD` is set or the
transcript is under a scratch root: the CLI enforces the exclusions the hook
does, finding 13). With `--nothing-durable`: mark the checkpoint consumed,
print one line, exit 0. Otherwise validate the payload against an allowlist
of exactly the four schema keys with their types, non-empty title and
summary, strings only inside the arrays (exit 2 with a one-line reason on
stderr, so the model can fix it and call again; unknown keys are rejected,
finding 14); redact; write the record (an existing key is left untouched,
"already recorded"); mark the checkpoint consumed with the job key; print
the accepted record as one JSON line; exit 0.

## The Stop hook

`hooks/claude-code/stop-record-episode.sh`:

    #!/bin/sh
    command -v atrium >/dev/null 2>&1 || exit 0
    exec atrium session-stop

registered under `Stop` in `~/.claude/settings.json`. Nothing else: no
daemon, no queue, no state outside the instance. `atrium` resolves the
instance from `SYNTOPICA_DATA` or the working directory like every other
command; the hook's `cwd` is the session's, so recording and recall resolve
the same instance.

## The backfill rule

`atrium synthesize` skips every conversation that already holds a
`session-self-v1` record, and counts it as covered. `--include-session-covered`
lifts that for a deliberate re-run. Serving stays the union: a session
episode and a batch episode never share an `episode_id`, and
`choose_served_records` keeps both. Overlap therefore exists only for a
conversation the batch lanes synthesized before its session started
recording (sessions alive during the rollout, resumed old sessions): a
few duplicate titles in recall during the transition, and no lost record.

## Residual loss, stated

- A session that never crosses the reminder limits, or whose model ignores
  the refusal three times, has no session record. For an operator with batch
  lanes the conversation is synthesized by them as today; for a person
  with none it is uncovered until they add one.
- Work after the last consumed checkpoint is not recorded by the session
  and, because the conversation is then skipped by the batch lanes, not by
  them either. The limits keep this tail under 32 KiB of transcript.
- After compaction the model records what it still knows of the interval.

## Not in this revision

No Codex or Cursor hook; no change to the batch segmentation, prompt or
schema; no promotion into the wiki (records stay in the reviewed tray); no
config surface beyond the two commands and one `synthesize` flag; no
timestamp-level backfill (the `session` field keeps the data for it).

## Verification

`uv run baseline-py gate` green, plus tests for: conversation id equals the
exporter's; episode id stable per boundary and different across boundaries;
job key independent of the batch prompt hash; re-key leaves a session record
unchanged; payload validation rejects a missing key, an unknown key, a
non-string fact, an empty title; redaction covers a private key block, an
assigned password and a bearer token through write, ingest and recall;
`session-stop` is silent on `stop_hook_active` with a consumed checkpoint,
on a scratch transcript, on `sdk-py`, under the limits, and with no user
prompt since the baseline; refuses above the limits and freezes a
checkpoint whose id the reason names; re-refuses twice after an ignored
instruction and then goes quiet; drops a checkpoint whose uuid vanished;
`record-session` with the frozen id writes a record carrying the frozen
boundary even after the transcript grew, is a no-op the second time, and
consumes the checkpoint with `--nothing-durable`; `ingest-synthesis` makes
the record reachable from `recent_episodes` with the cwd's project workspace
before any raw conversation is indexed; `synthesize` skips the conversation
unless `--include-session-covered`.

Live: one interactive session in this repository crosses the limits, the
refusal appears, one record lands in the instance registry, `atrium
ingest-synthesis` indexes it, `atrium recall --cwd .` lists its title.

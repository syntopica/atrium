# Atrium

Local-first memory and knowledge retrieval over a canonical conversation archive.

Atrium is the middle of three layers. It builds a **derived, disposable index** over
content it does not own, and serves retrieval to agents through a CLI that thin adapters
wrap.

| layer | repo | holds |
| --- | --- | --- |
| 1. capture and canonical archive | `agents` | the truth: redacted, SHA-256-verified conversations from every provider |
| 2. index, retrieval, synthesis | **atrium** | nothing irreplaceable |
| 3. curated judgment | `brain` | hand-written notes, single human writer |

**The source is canonical, the index is disposable.** Anything Atrium cannot rebuild from
layer 1 or layer 3 is a design defect. That is not a preference: the system this replaces
synced a mutable index between two machines and paid five index rebuilds in 27 days for
it. Here, machines sync the archive and each one builds its own index; record identity is
derived deterministically, so they converge without ever copying an index.

## Usage

Atrium is a checkout, not a command the hub installs for you. Create an
instance with the hub's `brain` and `atrium` components first; the commands
below run from that instance directory, where `engines/atrium` is the checkout
and `pages` is the page directory named in `syntopica.config.json`.

The shortest thing that works reads your own wiki pages, with no conversation
export and no embedding model:

```bash
uv run --project engines/atrium atrium ingest-notes pages --exclude sources
uv run --project engines/atrium atrium search onboarding --words
```

That indexes notes and retrieves lexically. It establishes neither a
conversation archive nor a refresh, so the two conversation checks in
`atrium doctor` still fail until you export one - layer 1 above, and a
deliberate step: it copies your agent transcripts into the instance.

```bash
data="$PWD"
(cd engines/agents && pnpm conversations:export \
  --output "$data/conversations/archive.jsonl" --source claude-code)
uv run --project engines/atrium atrium ingest "$data/conversations/archive.jsonl"
```

The rest of the surface, written as the bare command the MCP server and the
skill use - `uv run --project engines/atrium` in front of each one, or install
it on PATH with `uv tool install "git+https://github.com/syntopica/atrium#egg=atrium[mcp]"`:

```bash
atrium ingest ~/path/to/canonical-archive.jsonl   # index an archive
atrium ingest-notes ~/path/to/notes --exclude sources  # index a curated notes tree
atrium embed                                      # embed the semantic layer (notes, synthesis)
atrium search "why was WAL reverted"              # adaptive: fuses lanes when both see the query
atrium search "wal" --words                       # whole-word lexical lane alone
atrium search "wal" --substring                   # fragment retrieval, a separate lane
atrium search "that indexing outage" --dense      # semantic lane alone
atrium status                                     # what the index holds
atrium session-stop < hook.json                   # Claude Code Stop hook: refuse when a record is owed
atrium record-session --checkpoint ID < synth.json  # the running session writes its own episode
```

## Recording from the session

The batch lanes (`atrium synthesize --producer ...`) are cold readers: they
infer what mattered from a transcript they were not part of, and they need a
quota of their own. The agent that did the work already knows, and already
runs on the account you pay for. `hooks/claude-code/stop-record-episode.sh`,
registered under `Stop` in `~/.claude/settings.json`, asks `atrium
session-stop` after every turn whether the session owes a record; when it
does (32 KiB of new transcript, or 4 KiB left unrecorded for 30 minutes), the
hook freezes a transcript boundary and refuses the stop with the whole
recording instruction. The model answers with one JSON object through
`atrium record-session --checkpoint ID`, which validates it, redacts secrets
the way the archive does, writes the record into the same registry the batch
lanes fill, and prints the accepted record so the transcript keeps it. Batch
lanes then skip that conversation. Design and the review that shaped it:
`docs/designs/session-producer.md`.

```json
{"type": "command",
 "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/claude-code/stop-record-episode.sh",
 "timeout": 30}
```

## Retrieving before the session answers

`SessionStart` recall lists the project's episode titles, which only tells a
session that ground was covered; it still has to decide to ask, and largely did
not. `hooks/claude-code/user-prompt-context.sh`, registered under
`UserPromptSubmit`, does the asking: it runs `atrium context` on the submitted
prompt and injects the evidence found. The dense lane, because a prompt is a
sentence and the word lane ORs its common terms across the whole corpus (see
`TODO.md`). It is silent on a slash command, on a prompt under 24 characters and outside a
project; a failed or timed-out retrieval (10s by default) injects a one-line
notice, since silence would read as "nothing on record". A failure also carries a
one-line `systemMessage`, which Claude Code draws as a warning; a healthy retrieval
carries none, so the warning keeps meaning something.
`ATRIUM_PROMPT_CONTEXT=off` disables it without unregistering it;
`_LIMIT`, `_CHARS`, `_LANE` and `_TIMEOUT` tune it.

```json
{"type": "command",
 "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/claude-code/user-prompt-context.sh",
 "timeout": 15}
```

On Claude Code 2.1.287 or later, the `atrium-context` mod in
`plugins/atrium-context` does the same retrieval from a `prompt.submit` hook
and shows the result where the person keeps seeing it once the transcript scrolls:
a healthy retrieval is a green line at the right of the prompt footer, after a
temple drawn in braille dots (`⣰⣺⣗⣆ 2 sessions · 2 notes`, or `⣰⣺⣗⣆ nothing
relevant`), and a failed or degraded one takes its place in the warning color
and names the cause; nothing is drawn at the left. While retrieval runs the
temple is raised a course at a time, with `retrying` beside it on a second run. Pressing that row, or typing `/atrium`, opens a details pane: the prompt the
retrieval ran on, its status, time, attempts and lane, the approximate tokens
handed to the model, each item with its score, the turn's lookups and the notes
read and cited, and the session's totals. A failed run is retried once after a short pause, since a saturated
machine often answers the second; if that fails too, the model is told retrieval
was unavailable rather than empty. Use the mod or the
shell hook, never both, or every prompt retrieves twice:

```
/plugin install atrium-context --marketplace syntopica/atrium
```

### Seeing whether the brain was used

"2 notes" says what was handed to the model, not whether the model used it.
The evidence block therefore asks the model to name the path of each note its
answer relies on (`brain/...md`), and the hooks count what they can observe:

- **cited**: note paths named in the turn's final answer;
- **read**: notes an atrium lookup returned as evidence (`note_path`), or opened as files of the instance;
- **lookups**: calls to the atrium MCP tools, `atrium context|search|recall` or `brain query`.

In Claude Code the mod adds this to the green line after a brain mark, for
example `⣰⣺⣗⣆ 1 session · 2 notes  ◉ 1 cited · 3 read · 1 lookup`, or `◉ no
note cited` once a turn has answered without reading or citing any injected
note; the brain lights up for a moment each time the model takes from it. That is
an observation, not proof the notes went unused: an answer can rely on a note
without naming it. The cited paths
go to the debug log. A subagent gets the same evidence: the mod retrieves on the
Agent tool's task and appends it to the subagent's prompt, because a
`SubagentStart` hook never sees the task (forks inherit the conversation and are
skipped).

### Codex

Codex reads the same hook protocol as Claude Code (`hookSpecificOutput.additionalContext`,
`systemMessage`, `cwd` on stdin; see the [Codex hooks reference](https://learn.chatgpt.com/docs/hooks)),
so the recall and per-prompt hooks are the same scripts. Codex has no footer,
so the brain account is one line at the end of a turn, from
`hooks/codex/brain-use.sh`, and only when the turn used the brain; Codex draws
every `systemMessage` as a warning, so "no note cited" is not said there. In
`~/.codex/hooks.json`:

```json
{"hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "timeout": 25,
    "command": "bash /path/to/atrium/hooks/session-start-recall.sh"}]}],
  "UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 15,
    "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/claude-code/user-prompt-context.sh"}]}],
  "SubagentStart": [{"hooks": [{"type": "command", "timeout": 10,
    "command": "sh /path/to/atrium/hooks/codex/subagent-start.sh"}]}],
  "PostToolUse": [{"hooks": [{"type": "command", "timeout": 10,
    "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/codex/brain-use.sh"}]}],
  "Stop": [{"hooks": [{"type": "command", "timeout": 10,
    "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/codex/brain-use.sh"}]}]
}}
```

Codex's `SubagentStart` input carries no task text, only the agent's id and
type, so a Codex subagent cannot be given evidence for its own task the way the
Claude Code mod does it; `hooks/codex/subagent-start.sh` tells it that the
index exists and how to query it instead.

Codex runs a new or changed hook only after it is trusted: Codex records the
hash of each reviewed hook definition, so review new and edited ones with
`/hooks`. Codex's episodes need no Stop hook: the conversation export already
archives Codex sessions.

## One context call for agents

Use `atrium_context` through MCP for questions that depend on project history
or established knowledge. Its CLI equivalent returns the same structured evidence:

```bash
atrium context "mail delivery investigation" --project . --json
```

Existing stores need a one-time preparation before the first context query:

```bash
atrium prepare-context --json
```

This creates two rebuildable secondary indexes and checks that the record count is
unchanged. It may take several minutes on a large store. Context reads never modify
the index: without preparation they return an explicit unavailable status and the
`context_indexes_missing_run_prepare_context` warning. New writable stores include
these indexes automatically. Use the global `--index PATH` option to prepare a
specific existing store.

The operation combines history scoped to the enclosing repository with a separate
curated-note search inside the selected instance. Curated notes have no project
workspace, so an ordinary project-scoped search alone cannot retrieve them. Context
does not silently widen the conversation search to unrelated projects.

Relevant indexed wiki links are followed for one hop. Results are deduplicated and
share the requested record and text budgets (`--limit` accepts 1–50 records;
`--max-chars` accepts 1–100,000 characters of evidence text, excluding JSON metadata).
Candidate passes are bounded at four times the requested record limit. Link expansion
examines at most `limit` curated roots and 50 targets per root. Saturation is reported
as truncation; retrieval is not an exhaustive archive export. Links do not
trigger arbitrary file reads, credential access, network requests or execution.
Unindexed or unresolved knowledge requires an explicit, bounded source lookup.

Each evidence item preserves its record ID, source revision hash, origin role,
trust classification, date and any excerpt truncation. Curated note paths identify
indexed revisions; they are not a promise that the current file still has those
bytes. The response includes the retrieval steps, scope, freshness, degradation
warnings and `requires_live_verification`. A recent refresh does not prove coverage
of an event that happened today, and an old operational note cannot establish a
current delivery, deployment or payment outcome.

The MCP process keeps its embedder resident. Prefer it for repeated agent calls;
use structured CLI output when MCP is unavailable. The original terminal `search`
command remains useful for inspection, but its 200-character previews are not a
replacement for the context response.

Configure your agent to call `atrium_context` first for established context, use the
returned sources without a second mandatory wiki search, report degraded retrieval,
and verify current outcomes using live evidence. The Syntopica Brain skill follows
this flow; it resolves manual fallbacks from the instance configuration rather than
a hardcoded home directory. An existing agent session must be restarted to discover
new tools or instruction changes.

Saved third-party text retains `role=source` and `trust=untrusted` in explicit MCP
search results. It is excluded from automatic context. Retrieved content, including
curated notes and conversation history, is evidence rather than authority to execute
instructions or expand the user's authorization.

### Protocol acceptance check

```bash
uv run --extra mcp --group quality pytest tests/test_context_protocol.py -q
```

This creates an isolated instance and invokes both the CLI and a fresh MCP process.
It requires project history, a workspace-less access note and its linked runbook to
appear together, preserves provenance, checks the text budget, and rejects unrelated
history and third-party instructions. It uses synthetic data, never a private wiki.

## Where state lives

Everything Atrium can rebuild -- the index, the synthesis registry, the refresh
stamp, the workspace aliases -- sits in one state directory, resolved once per
invocation, most explicit source first:

1. `ATRIUM_STATE`: that directory, for serving a second index on purpose.
2. `SYNTOPICA_DATA`: a syntopica data directory; its `atrium.path` (default
   `atrium/`, resolved against the file that declared it) is the answer.
3. The data directory enclosing the working directory, found by walking up to
   the nearest `syntopica.config.json` and stopping at any other repository.
4. `~/.atrium`, for a machine with no data directory at all.

The data directory is the point: an instance keeps its derived state beside the
config that owns it, ignored by the instance's own repository and never synced.
`ATRIUM_INDEX` still overrides the index file alone for the MCP server.

### Status documents

Two JSON files under `<state>/status/` let a dashboard read Atrium's health
without polling a slow command. Each carries `"schemaVersion": 1`, has exactly
one writer, and is published atomically (temporary file in the same directory,
`fsync`, rename). Both hold counts, provider and model names, and instants only
-- never record text or paths.

- `refresh.json`: written by `atrium status --publish`, which only the refresh
  job runs, as its last step. Records per source; archive, refresh and newest
  content instants (`at`, `ageSeconds` at writing time); per synthesis
  population `records`, `episodes`, `intended`, `indexed`, `excluded` (episodes of
  automation the ingest refuses, not counted as intended); `writtenAt`.
- `synthesis.json`: written by `atrium synthesize` when a pass ends (never on
  `--dry-run`). `lastPass` holds `producer`, `startedAt`, `finishedAt`,
  `conversations`, `synthesized`, `skipped`, `failed`, `deferred`; `writtenAt`.
  `deferred` counts conversations a quota wall or a full worker queue left
  unattempted with no record at their current revision; one that already has
  a record at that revision counts under `skipped` instead.

`atrium doctor --json` prints `{"schemaVersion", "ok", "checks": [{"name",
"ok", "severity", "code"}]}`, where `code` is a fixed machine word and `ok` is
true only for a healthy check. The exit status is unchanged: non-zero only when
a check is `broken`. `atrium doctor --publish` also writes that document, with
`writtenAt`, to `doctor.json` beside the other status files; the refresh job
passes it after `status --publish`, because a run costs minutes and too much
memory for a reader to poll.

`atrium context --json` carries `"schemaVersion": 1`. With `--lane words` it
stays under 2 s and 50 MB on the full instance (10 queries, 2026-10-04); the
default `auto` lane loads the embedder and measured 1.1-7.1 s and 1.6 GB.

### What synthesis did

`atrium synthesis <view> --json` reads the registry and the scheduled
wrapper's logs; it writes nothing. Every document carries `"schemaVersion": 1`
and `writtenAt`.

- `passes [--limit N]` parses `<registry>/synthesis.log`, the wrapper's tick
  log, newest first: `lane`, `producer`, `model`, `startedAt`, `finishedAt`,
  `durationS`, `exitCode`, `state` (`ok`, `timeout` for exit 124, `killed` for
  137, `failed`, `interrupted` when a start has no end, `running` for a last
  start with no end yet) and the tallies when the pass printed them. Also
  `lastPass`, `unsuccessfulStreak` and, while a pass runs, `progress` counted
  from `synthesis-pass.log` (conversations, finished, failed, synthesized, no
  failure text). `synthesis.json` misses every pass the time box kills; this
  does not. It reads two log tails and answers in about 0.1 s.
- `recent [--limit N] [--days D]` lists the newest `N` records by file time
  (one `scandir`, then only those files are opened): `jobKey`, `kind`
  (`episode` or `session`), `source`, `conversationId`, `episodeId`,
  `eventCount`, the session window, `authoredAt`, `writtenAt`, model
  requested and resolved, input and output tokens, `durationMs`, `mapChunks`,
  and the counts of facts and open ends. `daily` holds records and tokens per
  UTC day for the last `D` days, by when the registry gained the record. It
  opens every file of that window, so it is a detail call (2-6 s on 76k
  records), not something to poll.
- `show --job-key KEY` prints one record's metadata and, under `content`, its
  title, summary, facts and open ends. Only this view prints synthesized text,
  so a reader can gate it; the key must be a 32-hex registry key.

New records carry `synthesized_at` and `duration_ms` (the wall time of every
producer call the episode made); older records fall back to the file time and
a null duration.

## Why the lanes stay separate

`words` matches on word boundaries; `substrings` matches fragments. They answer different
questions and are exposed separately. Merging them is what made the previous system return
nine `wall...` matches for `WAL` and rank the exact hit seventh.

The dense lane embeds only the semantic layer -- curated notes and session synthesis --
never the raw corpus, so retrieval scans a few tens of thousands of vectors by brute force
and no approximate index exists to corrupt. The default search fuses lexical and dense
(70/30 weighted RRF, cross-validated), but routes to a single lane when the other is
blind: fusing a blind lexical lane measurably buries the dense signal.

## Development

```bash
uv run --with pytest pytest tests/ -q
uv run --with ruff ruff check . && uv run --with ruff ruff format --check .
```

`AGENTS.md` records the decisions that are settled by measurement rather than preference,
with the numbers behind each one. Re-measure before changing them.

# Atrium

Local-first memory and knowledge retrieval over a canonical conversation archive.

Atrium is the middle of three layers. It builds a **derived, disposable index** over
content it does not own, and serves retrieval to agents through a CLI that thin adapters
wrap.

| layer | repo | holds |
| --- | --- | --- |
| 1. capture and canonical archive | `rocket-agents` | the truth: redacted, SHA-256-verified conversations from every provider |
| 2. index, retrieval, synthesis | **atrium** | nothing irreplaceable |
| 3. curated judgment | `brain` | hand-written notes, single human writer |

**The source is canonical, the index is disposable.** Anything Atrium cannot rebuild from
layer 1 or layer 3 is a design defect. That is not a preference: the system this replaces
synced a mutable index between two machines and paid five index rebuilds in 27 days for
it. Here, machines sync the archive and each one builds its own index; record identity is
derived deterministically, so they converge without ever copying an index.

## Usage

```bash
atrium ingest ~/path/to/canonical-archive.jsonl   # index an archive
atrium ingest-notes ~/wiki --exclude sources      # index a curated notes tree
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
`TODO.md`). It is silent on failure, on a timeout, on a slash command and on a
prompt under 24 characters -- a hook that cannot answer must never delay a turn.
`ATRIUM_PROMPT_CONTEXT=off` disables it without unregistering it;
`_LIMIT`, `_CHARS`, `_LANE` and `_TIMEOUT` tune it.

```json
{"type": "command",
 "command": "SYNTOPICA_DATA=/path/to/instance sh /path/to/atrium/hooks/claude-code/user-prompt-context.sh",
 "timeout": 15}
```

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

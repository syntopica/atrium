# Atrium — repository instructions

## What this is

Atrium is layer 2 of a three-layer memory system: it builds a **derived, disposable index**
over content it does not own, and serves retrieval to agents.

| layer | owner | holds |
| --- | --- | --- |
| 1. capture and canonical archive | the agents repository | the truth: redacted, SHA-256-verified conversations |
| 2. index, retrieval, synthesis | **this repo** | nothing irreplaceable |
| 3. curated judgment | the wiki | hand-written notes, single human writer |

**The rule that governs every decision here: the source is canonical, the index is
disposable.** Anything Atrium cannot rebuild from layer 1 or layer 3 is a design defect.
That rule is not aesthetic — syncing a mutable index between machines cost five index
rebuilds in 27 days on the system this replaces.

## Hard boundaries

- **Never read provider transcripts directly.** Ingest reads the canonical archive only.
  Reading `~/.claude/projects` or any provider path from this repo re-introduces the
  redaction bypass that put 14 private-key blocks into the previous index.
- **Never write to layer 1 or layer 3.** Proposals to `brain` are files an operator
  reviews, never direct commits.
- Never sync the index between machines. Sync the archive; each machine rebuilds.
  The state directory sits inside the data directory (`atrium.path` of the
  instance, see README "Where state lives") and is ignored by its repository;
  living beside layer 3 does not make it part of layer 3, and nothing here
  writes a page.
- **Role `source` is the untrusted-origin mark** (saved third-party content,
  e.g. brain's `sources/`, ingested with `ingest-notes --third-party`). It must
  never enter `SEMANTIC_ROLES`, never be embedded, and never reach session-start
  injection; it stays lexically searchable on request, displayed with its mark.
  A retrieved instruction inside third-party text can steer a tool-bearing agent.
- **A bulk job on nova runs capped in memory and CPU, or elsewhere.** nova serves
  production: an uncapped embedding run OOM-killed its MariaDB (2026-10-12), and two
  memory-capped units holding ~19 of 32 cores starved Apache into `MaxRequestWorkers`
  (2026-10-14). Use a transient unit (`systemd-run --scope -p MemoryMax=<n>G -p
  CPUQuota=<=400%`) in the day, or the night window; check load and Apache worker
  headroom before launching.

## Measured decisions

These are settled by measurement, not preference. Re-measure before changing them.

- **Embedder: `embeddinggemma-300m`, 384 dims, CPU.** The English-only default of the
  previous system scored R@10 40.8% on a 365-pair set from this corpus, 77% of which is
  Spanish; the multilingual model scored **70.4%**. On CoreML this model silently returns
  NaN or zero vectors, so CPU is required and vectors must be validated.
- **Fusion: 70% lexical / 30% dense, weighted RRF, k=60.** Swept 0-100% in 0.05 steps,
  five-fold held out. Reached R@10 80.0% / MRR 0.635 against 77.3% / 0.580 for lexical
  alone.
- **The dense lane stays separately addressable.** On queries sharing no informative word
  with their answer, lexical scores 0% and fusion *suppresses* the dense signal
  (12% -> 8% R@10). Never expose only the fused list.
- **Word-level lexical is separate from substring search.** The previous system's trigram
  FTS returned nine `wall...` false positives for `WAL`, with the first exact hit ranked
  seventh.

## Sensitive retrieval diagnostics

- Never print raw retrieval evidence while investigating credential exposure. Inspect metadata and redacted summaries only; use synthetic sentinel values for reproduction and regression tests.
- Treat output redaction as a separate boundary from archive redaction. Review MCP text content, structured content, CLI serialization and injected context; Markdown tables and curated notes can contain secrets even when archive ingestion is sanitized.
- Record the affected source path and field names without copying credential values. Preserve canonical evidence; source edits and credential rotation require separate authorization.

## Conventions

- Python, snake_case, ruff-formatted, double quotes. Tests are `tests/test_*.py`.
- One exported unit and one responsibility per file; every dependency an explicit import.
- All code, comments, docs and commit messages in English.
- No SQL in Python literals (codeality-py `BPY006`): every statement is a file under
  `atrium/sql/<area>/<name>.sql`, loaded with `atrium.sql.load_sql.load_sql`; test SQL
  lives in `tests/sql/` and loads with `tests/load_test_sql.py`. `{name}` fields are for
  code-built identifiers and fragments only; user values stay bound parameters.
- Gates: `uv run codeality-py gate` and `pnpm dlx @syntopica/db-quality@0.6.0 gate`. The
  second plans every `atrium/sql` statement against `.atrium-index.sqlite3`, an ignored
  local symlink to the live index (absent: `BDB406` is skipped). Deliberate full scans
  (status counts, doctor and ingest batches, `LIMIT 1` probes) are carried in
  `.codeality-db-baseline.json`.

<!-- tadu:rule v4 -->

## Continuous TODO, Work Log, and History Coverage

Keep the active backlog and the searchable record of closed work with tadu. A
repository uses `TODO.md` and `TODO_LOG.md` (format 1), or one JSON file per
task under `todo/` (format 2, when `todo/tadu.json` exists). Use
`TODO_HISTORY_INDEX.jsonl`, when present, to avoid parsing unchanged
conversations more than once.

- Do not read the backlog files whole: query them. `tadu list` filters with
  `--category`, `--type`, `--text`, `--due-within N`, `--overdue`,
  `--min-priority`, `--open` (pending work only) and `--history`; `tadu ready`
  lists what can start now; `tadu show KEY` prints one item. When more items
  follow, a list says so on stderr: page with `--offset` or narrow the filter.
- Before recording work or reopening an old task, run `tadu similar "<title>"`
  and update the existing item instead of creating a duplicate.
- Record actionable bugs, risks, blockers, deferred work, missing tests,
  validation, documentation, and product improvements as they are discovered.
- Use `[ ]` pending, `[~]` partial or unverified, `[!]` blocked, `[x]` verified
  complete, `[-]` obsolete or superseded (in format 2: pending, in_progress,
  blocked, done, cancelled). Keep blockers open and name the smallest action
  required to unblock them.
- Format 1: when work becomes `[x]` or `[-]`, remove it from `TODO.md` and add
  a dated entry to `TODO_LOG.md` under `## YYYY` and `### YYYY-MM` headings, in
  the shape below. An `[x]` entry needs an `Evidence:` line and a `[-]` entry a
  `Resolution:` line, each with content.
- Format 1: give an item a `Kind:` field when it is clear what it is: `task`
  for work you can do, `decision` for a choice a person must make, `waiting` for
  something someone else owes, `later` for something not to do now. Leave it
  out when unclear. `Due:` is the deadline, `Check on:` the day to look at the
  item again and `Not before:` the day before which it cannot start.
- Take work with `tadu next`; `tadu inbox` lists what waits on a person and
  `tadu urgent` what is urgent. When only a person can answer a question while
  you work alone, record it (format 1: `tadu add --kind decision`; format 2: a
  task of type `decision`), block the task it holds up (format 1:
  `tadu mark --state blocked --note "<blocker>"`; format 2: add the decision to
  its `blocked_by` with `tadu set`), and go on with the next task.
- Format 2: never edit task files by hand. Use `tadu add` (with category, type
  and priority), `tadu set ID key=value`, `tadu claim ID --as agent:<name>`
  before working on a task, and `tadu close --id ID --evidence "<proof>"`
  (`--resolution`, or `--duplicate-of ID`). Close reports the tasks that no
  longer wait on it; decide for each whether it moves to pending. Every command
  is a dry run until `--write`.
- Before reviewing past conversations, consult the history index and skip
  unchanged records already marked `complete` or `irrelevant`. Update a record
  only after its findings are reconciled; interrupted work stays `partial`.
- Do not interrupt the active task for unrelated non-critical work, and do not
  implement unrelated TODO items unless requested. Immediately report critical
  security, destructive, or data-loss findings. Never put secrets in the
  backlog.

```md
- [x] YYYY-MM-DD — **Category:** What was done.
  - Result: What changed.
  - Evidence: The test, command result, commit or PR that proves it.

- [-] YYYY-MM-DD — **Category:** What was dropped.
  - Resolution: Why it no longer applies, or what replaced it.
```

In format 1, close an item with
`tadu close --match "<text>" --evidence "<proof>" --write` (`--resolution` for
`[-]`, `--result` for the Result line); it moves the item and writes the entry
in this shape. `add`, `mark` and `close` print a diff and write only with
`--write`; a connected `tadu mcp` server offers the same tools. Run
`tadu doctor .` after changing the backlog and before committing. If `tadu` is not
on PATH, install it as https://github.com/syntopica/tadu#install describes, or report that it is
missing. Formats: tadu spec v1,
https://github.com/syntopica/tadu/blob/main/spec/todo-format-v1.md, and v2,
https://github.com/syntopica/tadu/blob/main/spec/todo-format-v2.md. The
tadu-create and tadu-work skills automate these workflows and are optional.
<!-- /tadu:rule -->

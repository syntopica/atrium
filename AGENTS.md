# Atrium — repository instructions

## What this is

Atrium is layer 2 of a three-layer memory system: it builds a **derived, disposable index**
over content it does not own, and serves retrieval to agents.

| layer | owner | holds |
| --- | --- | --- |
| 1. capture and canonical archive | `~/p/agents` | the truth: redacted, SHA-256-verified conversations |
| 2. index, retrieval, synthesis | **this repo** | nothing irreplaceable |
| 3. curated judgment | `~/p/wiki` | hand-written notes, single human writer |

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

## Conventions

- Python, snake_case, ruff-formatted, double quotes. Tests are `tests/test_*.py`.
- One exported unit and one responsibility per file; every dependency an explicit import.
- All code, comments, docs and commit messages in English.

## Continuous TODO, Work Log, and History Coverage

Maintain `TODO.md` as the active backlog and `TODO_LOG.md` as the searchable
record of closed work. Use `TODO_HISTORY_INDEX.jsonl` to avoid parsing unchanged
conversations more than once.

- Read `TODO.md` at the beginning and end of related work. Search `TODO_LOG.md`
  before reopening an old task or repeating a previous solution.
- Record actionable bugs, risks, blockers, deferred work, missing tests,
  validation, documentation, and product improvements as they are discovered.
- Update an existing entry instead of creating a duplicate. Keep entries concise
  and under the most relevant category.
- Use `[ ]` pending, `[~]` partial or unverified, `[!]` blocked, `[x]` verified
  complete, `[-]` obsolete or superseded. Keep blockers in `TODO.md` and name
  the smallest action required to unblock them.
- When work becomes `[x]` or `[-]`, append a dated entry with concise result and
  evidence to `TODO_LOG.md`, then remove it from the active backlog. Keep one
  log file, grouped by year and month.
- Before reviewing past conversations, consult the history index and skip
  unchanged records already marked `complete` or `irrelevant`. Update a record
  only after its findings are reconciled; interrupted work stays `partial`.
- Do not interrupt the active task for unrelated non-critical work, and do not
  implement unrelated TODO items unless requested. Immediately report critical
  security, destructive, or data-loss findings.

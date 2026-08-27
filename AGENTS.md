# Atrium — repository instructions

## What this is

Atrium is layer 2 of a three-layer memory system: it builds a **derived, disposable index**
over content it does not own, and serves retrieval to agents.

| layer | owner | holds |
| --- | --- | --- |
| 1. capture and canonical archive | `~/p/rocket-agents` | the truth: redacted, SHA-256-verified conversations |
| 2. index, retrieval, synthesis | **this repo** | nothing irreplaceable |
| 3. curated judgment | `~/p/brain` | hand-written notes, single human writer |

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

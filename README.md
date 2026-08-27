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
atrium search "why was WAL reverted"              # whole-word lexical retrieval
atrium search "wal" --substring                   # fragment retrieval, a separate lane
atrium status                                     # what the index holds
```

## Why two lexical lanes

`words` matches on word boundaries; `substrings` matches fragments. They answer different
questions and are exposed separately. Merging them is what made the previous system return
nine `wall...` matches for `WAL` and rank the exact hit seventh.

## Development

```bash
uv run --with pytest pytest tests/ -q
uv run --with ruff ruff check . && uv run --with ruff ruff format --check .
```

`AGENTS.md` records the decisions that are settled by measurement rather than preference,
with the numbers behind each one. Re-measure before changing them.

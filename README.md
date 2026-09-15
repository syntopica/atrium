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
atrium ingest-notes ~/p/wiki --exclude sources   # index a curated notes tree
atrium embed                                      # embed the semantic layer (notes, synthesis)
atrium search "why was WAL reverted"              # adaptive: fuses lanes when both see the query
atrium search "wal" --words                       # whole-word lexical lane alone
atrium search "wal" --substring                   # fragment retrieval, a separate lane
atrium search "that indexing outage" --dense      # semantic lane alone
atrium status                                     # what the index holds
```

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

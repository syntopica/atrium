# Retrieval: query prompt, reranker, document prompt

Status: plan, 2026-10-15. Owner: "look at it with Codex, make a plan, and go".
Measurements behind it are in `TODO.md` (Measurement) and in the instance at
`atrium/evaluations/ideas-2026-10-14/`.

## What was measured

85 labeled questions (`evaluations/acceptance-2026-10-11/labeled.jsonl`), R@10 /
MRR@10 on the context surface, word and dense lists fused by RRF at w=0.5:

| Variant | R@10 / MRR |
|---|---|
| production: `task: sentence similarity | query: ` on queries and documents | 0.35 / 0.19 |
| query prompt `task: search result | query: `, documents unchanged | 0.40 / 0.23 |
| query prompt plus document prompt `title: <title or none> | text: ` | 0.44 / 0.24 |
| cross-encoder `BAAI/bge-reranker-v2-m3` over the depth-30 candidates | 0.46 / 0.33 |

**Codex review, 2026-10-15: these numbers do not measure production.** The
captures route each question to the curated or history pass by the labeled
answer's kind (an oracle), fuse at w=0.5 where production uses 0.7 history /
0.3 curated (`context_hits.py:83-85`), and skip interleaving, links,
retirement demotion and the evidence budget (`retrieve_context.py:134-157`).
The rerank scored the union of four depth-30 lists (30-119 pairs a question,
6,894 in all) and fused by conversation, while production fuses by record.
Every choice was also tuned and judged on the same 85 questions. And all of it
predates the 2026-10-14 admission cut and forget pass.

## Steps

### 0. An honest harness (done first)

- `evaluations/retrieval-2026-10-15/e2e.py` (instance, private) calls the real
  `retrieve_context` per question: both populations, production weights, links,
  retirement handling and the evidence budget, with the live dense matrix. It
  reports R@k and MRR@k over all 85 and over the answerable ones (an answer
  with no admitted record left, such as a deleted brain page, is reported
  apart), per stratum.
- The query prompt is the only variable at first: the stored vectors stay as
  they are, so the comparison needs no re-embed.
- A held-out set is generated only if a variant wins on these 85: same sampler
  with a new seed and sources disjoint from the first set, GPT-6 questions and
  judging, Claude audit. The decision is confirmed there, not on the set that
  chose it.

### 1. Query prompt

- Done without behavior change (`5bfdd9c`): `query_embedder` builds every query
  embedder (lazy, resident, search, context service) from `QUERY_PREFIX`;
  stored vectors and curation keep `DOCUMENT_PREFIX` (`page_shortlist.py:30`
  stays on the document recipe until measured on its own). Both are still the
  similarity prompt.
- Flip `QUERY_PREFIX` only if the end-to-end harness and the held-out set agree.
  Re-measure the 0.7/0.3 lexical weights per population after a flip.

### 2. Reranker

- Rescore exactly what production would rerank: the fused candidate list
  `retrieve_context` builds before evidence selection, at a fixed depth,
  per population, by record.
- Implement in shared retrieval (so the service, the in-process fallback and
  MCP agree), disabled by default, bounded, with a timeout fallback to the
  fused order and its own step timing; deterministic ties; thread-safe under
  the threaded `ContextServer`.
- Benchmark cold and warm p95 through the socket on this Mac under normal
  memory pressure. Ship only if added p95 < 1.5 s and quality holds on the
  held-out set.

### 3. Document prompt

Later: a full re-embed (about 22 h here, or nova's batch slice at night) behind
a vector recipe stamp the service checks, swapped per generation. Not part of
this pass.

## Out of scope

Distillation, supersession and the rest of `docs/designs/memory-lifecycle.md`.

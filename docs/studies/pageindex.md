# PageIndex study (2026-11-12)

Source: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex), MIT, Python. It builds one tree per long PDF (node title, page range, summary, children), keeps no vector store and no chunks, and answers with an agent loop that reads the tree, opens a section, judges whether it is enough and repeats. Its 98.7% FinanceBench figure is a vendor claim against a vendor-chosen baseline; no per-query latency is published.

Adopting it as-is does not fit Atrium: the corpus is short notes and conversations, not 100-page PDFs, and a variable-length agent loop cannot run inside the prompt hook (a live `atrium context` already takes about 3.9 s with partial rerank). The question was which of its ideas help Atrium's curated notes.

## Method

- Set: the 39 questions from `acceptance-2026-10-11` and `holdout-2026-10-15` (`~/p/wiki/atrium/evaluations/*/labeled.jsonl`) whose answer is a brain note (`"note" in strata`); 25 of them are no-overlap. Gold = `answer_conversation_id` plus `also_answers`.
- Scoring at page level: H@1, H@3, H@8, MRR@8.
- Corpus: read-only export of the live index, 6,874 note chunks (`provider='brain'`, `role='note'`) over 467 pages, with their stored vectors.
- Lexical leg: in-memory FTS5 with the production tokenizer (`unicode61 remove_diacritics 2`), AND pass then OR fill, top 32. It lacks `selective_expression`, so it compares variants with each other, not with production.
- Dense leg: cosine over `Embedder()` vectors, top 32. Re-embedding the unchanged text reproduced the stored vectors (max diff 1.01e-06).
- Fusion: `fuse_ranked` with the curated lexical weight 0.3; optional `CrossEncoder` rerank of the fused top 32.
- 39 questions is small: a difference of one or two hits is noise.

## A. Heading path and summary inside the chunk text

Variants: `path` = `Title › H2 › H3` + newline + chunk text; `path+summary` = path + ` — ` + frontmatter `summary:` + newline + text (385 of 467 pages have a summary). Both re-embedded in full.

| Variant | dense MRR | fused MRR | reranked H@1 | reranked H@8 | reranked MRR |
|---|---|---|---|---|---|
| base | 0.511 | 0.435 | 0.462 | 0.769 | 0.576 |
| path | 0.519 | 0.480 | 0.462 | 0.769 | 0.549 |
| path+summary | 0.513 | 0.475 | 0.436 | 0.692 | 0.533 |

Finding: the path helps fusion without rerank, but the cross-encoder already recovers it and ends slightly ahead on base. Not worth a full re-embed. Do not implement.

## B. LLM navigation over the page tree

Two calls per question through `agy`, prompt rule: "You are a retrieval router over a private knowledge base. Do not use any tool, do not read files: answer only from the text below. Reply with ONE line of JSON and nothing else."

1. Tree call. Input: the question and one line per page, `path | title | summary[:200]` (the frontmatter summary, or the first 160 characters of the body when absent), sorted by path, about 96 KB for 467 pages. Output: `{"pages": [...]}`, up to 6 paths, best first.
2. Outline call. Input: the question and, for each picked page, `## path | title | summary` followed by its H2 lines and indented H3 lines (at most 80). Output: up to 8 paths that contain the answer, best first, only from the given paths. If empty, fall back to the first call's order.

Paths not in the page set are dropped. 4 questions in parallel, 300 s subprocess timeout, 3 retries.

B2 variant: one call ranks the dense top-15 pages, shown with title, summary and outline.

| Method | H@1 | H@3 | H@8 | MRR | no-overlap H@8 / MRR | median latency |
|---|---|---|---|---|---|---|
| Reranked baseline (A, base) | 0.462 | - | 0.769 | 0.576 | - | - |
| B, `gemini-4-argon --effort medium` | 0.692 | 0.872 | 0.872 | 0.774 | 0.88 / 0.767 | 25.6 s |
| B, `gemini-3.8-flash --effort low` | 0.615 | 0.769 | 0.769 | 0.684 | 0.76 / 0.673 | 10.7 s |
| B2, `gemini-4-argon --effort low` | 0.615 | 0.744 | 0.769 | 0.686 | 0.64 / 0.57 | 8.8 s |

Argon run: 0 errors; the tree call picked the answer page in 34 of 39. B2 is capped by dense recall: the answer page is in the dense top 15 for only 0.769 of questions (0.64 for no-overlap).

Finding: tree navigation is the best page finder measured, +0.20 MRR over the reranked baseline, with the gain concentrated on no-overlap questions where lexical and dense fail. Its latency rules it out of the prompt hook.

## Implementation proposal

Build an explicit deep mode, never part of the hook:

1. `atrium navigate "<question>" [--project .] [--json]` and an MCP tool `atrium_navigate`, returning ranked brain pages with the matched H2/H3 sections and their text excerpts (through the same redaction boundary as `atrium_context`).
2. Tree source: built from the indexed note records (page path, title, frontmatter summary, H2/H3 headings), cached per index generation, not from the wiki files at query time.
3. Lane: `agy` first per the model routing order; Flash low as the default (10.7 s), Argon medium as `--thorough`. No API keys.
4. Agents call it when `atrium_context` comes back weak or for questions phrased without the note's vocabulary.
5. Gate before any default use: rerun on the full 85 + 88 sets and on a fresh, blinded question set; record latency p50/p95 and failure rate.

Open questions: whether conversations (not only notes) need a tree of their own; whether a two-level `brain/index.md` with an H2 map per page gives part of the gain for free (the index-first-try pilot missed the Redis question only because the answer sat under an H2 of `projects/nubenode-ops.md`).

The experiment scripts (`export.py`, `variants.py`, `embed.py`, `evaluate.py`, `nav.py`, `nav2.py`) and per-question outputs are in `~/p/wiki/atrium/evaluations/pageindex-2026-11-12/`, which is local only (ignored by the wiki repository).

# Other memory projects, November 2026

Research snapshot: 2026-11-06, from GitHub source, release notes, issues and
documentation read that day. It follows the 22-system study of 2026-10-14,
whose eleven ideas were measured on 2026-10-15 and 2026-10-16: file context,
the relevance cut, `atrium gaps` and `remember` were adopted; per-fact
vectors, recency, ES/EN expansion and the entity graph were measured and
dropped; the per-conversation diversity cap changed nothing. None of those is
reopened here. This pass looks only at the problems open in `TODO.md` today.

Evidence levels: "source" means the mechanism was read in the project's code;
"measured" means someone published a number; "claimed" means the number is the
vendor's own and was not reproduced. Nothing below was measured on Atrium yet.

## 1. Prompt-time retrieval under load

No project runs a local cross-encoder on the synchronous prompt path under a
fixed budget, as Atrium does. None documents behaviour under CPU contention.

- **claude-mem** (thedotmack/claude-mem, v15.10.0): per-prompt injection of up
  to 20 observations (`src/shared/semantic-context.ts`), skipped for prompts
  under 20 characters; fail-open with empty context when the worker is down; a
  single 15 s budget split between hook and server (`src/cli/handlers/session-init.ts`).
  No reranker. Source.
- **memsearch** (zilliztech/memsearch): the UserPromptSubmit hook does no
  retrieval; it prints a hint and the agent searches through a forked
  `memory-recall` skill (`plugins/claude-code/hooks/user-prompt-submit.sh`).
  Remote rerank is optional: Recall@5 0.747 without, 0.794 with Jev, 0.819 with
  Voyage (`evaluation/reranking-evaluation.md`, 2026-09-20). Source, measured by
  the vendor.
- **OpenViking** (volcengine/OpenViking): `openviking/retrieve/rerank_scoring.py`
  flags each document `reranked` and keeps the first-stage score for those the
  model did not score; it falls back wholesale only when the reranker raises or
  returns the wrong count. Source.
- **mem0** (`docs/components/rerankers/optimization.mdx`): 50 candidates for the
  local cross-encoder (`ms-marco-MiniLM-L-6-v2`), 30 for HuggingFace, 20 for an
  LLM reranker. Atrium reranks 64. Guidance, not measured.
- **MemOS**: a `cosine_local` reranker tier (numpy cosine) next to remote BGE,
  10 s timeout (`src/memos/reranker/factory.py`). Source.
- basic-memory, Graphiti, Letta, cognee, supermemory: no budgeted local rerank
  on a hook path found.

Ideas to test: keep a partial rerank (scored head by cross-encoder, unscored
tail in fused order); rerank fewer candidates first (16-24) and widen only with
time left; skip retrieval for prompts under ~15 characters.

## 2. Synthesis cost and backlog

- **claude-mem** synthesizes per tool use through the Claude Agent SDK with the
  `haiku` alias, the same model Atrium moved to on 2026-11-05. It has a quota
  guard that pauses the observer at a subscription usage threshold, skips noisy
  tools, caps replies at 4,096 tokens with thinking off, and keeps the prompt
  prefix stable for caching. Source and docs.
- **LightMem** (arXiv 2510.18866): filter and compress before extraction;
  "up to 38x" fewer tokens. Claimed.

Ideas to test: a quota guard for the Haiku tick; head/tail truncation of large
tool outputs before the model sees them; a byte-identical prompt prefix.

## 3. Faithfulness of synthesized episodes

No project publishes faithfulness numbers for session summaries. HaluMem
(arXiv 2511.03506) is the only independent measurement found: Mem0 extraction
accuracy 60.9%, update omission 74%; Zep best at updates, 47% correct; on
conversational data, not coding sessions. Atrium's blind judgments are ahead
of what the field publishes.

- **Graphiti** (`graphiti_core/prompts/extract_edges.py`): facts only if
  "clearly stated or unambiguously implied"; each edge carries
  `episode_indices`; names outside a given entity list are rejected; a
  contradicted edge gets `expired_at` and is kept. Source.
- Mem0 moved to ADD-only extraction because overwrite and delete lost
  information (its migration guide); supermemory marks `isLatest`.

Ideas to test: each fact cites message indices, and a deterministic check drops
facts whose citations do not exist or whose "applied/done" claim has no
matching tool result; the summary is written from the surviving facts only; the
episode outcome is an enum (`confirmed_in_transcript`, `not_stated`, `failed`,
`unknown`). Measure on the same 24 episodes as the 2026-10-16 comparison.

## 4. Index size and FTS5 compaction

- **claude-mem** hit the same failure: issue #2793, a 136 GB database holding
  0.02 GB of observations, recovered to 48 MB. Its
  `src/services/infrastructure/FtsMaintenance.ts` runs FTS5 `merge` in bounded
  steps (256 pages, 25 ms pause, stop when fewer than 2 changes) 60 s after
  start, and notes that VACUUM alone cannot compact an FTS index. User prompts
  get no FTS index and are searched with `LIKE`. Source.
- SQLite's FTS5 documentation: `detail=none` is suggested for an index used
  only for LIKE/GLOB; deleted rows persist until merged; `optimize` merges all
  segments; `merge` with a page count works incrementally; `contentless_delete=1`
  exists from 3.43.0. Official docs.

Ideas to test: an `atrium compact` command (bounded `merge`, then `optimize`,
then `VACUUM`, under `refresh.lock`); on a copy, the size and latency of a
`detail=none` trigram table against a `words` prefilter plus `instr()`.

## 5. Secrets in retrieved output

- mem0 issue #6817 (open since 2026-08-05): recalled memory returned
  unredacted, the hole Atrium closed on 2026-11-05.
- claude-mem strips `<private>` tags and runs 34 opt-in vendor regexes at
  capture only, with no output-side redaction (docs, auto-redaction page).
- No project found uses gitleaks, detect-secrets or trufflehog internally.

Idea to test: use a published pattern list (gitleaks rules) as a regression
corpus for `redact_sensitive_text`, plus an entropy check on value cells of
label/value tables.

## 6. Evaluation

- A LoCoMo audit (Penfield, 2026-04-04) found 6.4% of the answer key wrong and
  a judge that accepted 62.8% of adjacent wrong answers; vendor numbers on it
  are not comparable.
- Pooling (Upadhyay et al. 2024, arXiv 2405.04727): unjudged documents bias
  against systems outside the pool.

Idea: the fresh-judgment item in `TODO.md` should pool the top-k of every
system, strip system labels, shuffle, and report unjudged@k per system.
LongMemEval-S is the external set to add.

# Mem0 study

Research snapshot: 2026-08-27. This note separates Mem0 Platform from Mem0
Open Source (OSS), because the current products share an API shape but not every
storage or retrieval feature.

## What it is and how it works

Mem0 is a memory service and self-hostable library that sits between an
application and its model. The application sends useful interaction turns to
`add`, queries `search` before a later model call, and chooses which returned
memories enter the prompt. By default it stores extracted facts rather than a
verbatim transcript. [How Mem0 Works](https://docs.mem0.ai/core-concepts/how-it-works)

The write path first retrieves related existing memories, uses an LLM to extract
durable facts, deduplicates and embeds those facts, and extracts entities. The
current algorithm is additive: automatic extraction adds facts; corrections and
removals use explicit operations. `infer=False` bypasses extraction and stores
raw input, but can create duplicates if mixed with inferred writes.
[Add Memory](https://docs.mem0.ai/core-concepts/memory-operations/add)

Current documentation names three stores: SQL for facts and metadata as Mem0's
source of truth, a vector database for embeddings, and an entity store. Platform
retrieval combines semantic, keyword, entity, and temporal signals. OSS uses a
configured vector store and optional reranker; current OSS documentation says
graph memory is Platform-only. Provider choices include Qdrant, pgvector,
Chroma, Pinecone, Redis, Weaviate, Milvus, and Elasticsearch.
[Architecture](https://docs.mem0.ai/core-concepts/how-it-works#where-memories-live)
[OSS configuration](https://docs.mem0.ai/open-source/configuration)

Memories are scoped with `user_id`, `agent_id`, `app_id`, `run_id`, and metadata
filters. This is an access and lifecycle boundary, distinct from entities found
inside memory text.
[Entity-scoped memory](https://docs.mem0.ai/platform/features/entity-scoped-memory)

The active repository provides Python and TypeScript SDKs, a CLI, and a
self-hosted server. Its README also warns that managed benchmark results include
proprietary Platform optimizations, so they should not be treated as OSS results.
[mem0ai/mem0](https://github.com/mem0ai/mem0)

## Mechanisms it implements well

- Encode: context-aware LLM fact extraction, optional raw storage, metadata,
  embeddings, and entity extraction.
- Retrieve: scoped vector search, keyword and entity signals on Platform,
  temporal scoring, thresholds, and optional second-pass reranking.
- Consolidate: Platform Dream synthesizes higher-order patterns and links each
  pattern to its source memories. The synthesis is additive and idempotent.
- Forget: explicit update and delete operations plus expiration dates. Dream
  supersedes stale facts without deleting history.
- Scope: first-class user, agent, app, and run identifiers, with compound
  filters at read time.
- Dedupe: related-memory lookup on write and Dream Merge for exact or near
  duplicates. Merged records retain a link to the canonical record.
- Rerank: managed rerankers on Platform and configurable providers in OSS.

Dream's strongest idea is not generic summarization. It splits maintenance into
three explicit operations: Synthesis creates a derived pattern, Supersede links
an outdated fact to its replacement, and Merge links a duplicate to a canonical
memory. Source records remain reviewable.
[Dream](https://docs.mem0.ai/platform/features/dream)

## What Atrium should steal

1. Steal typed consolidation outcomes: `synthesized`, `superseded`, and
   `merged`. WHY: these states let retrieval prefer current, nonduplicate
   material without destroying history. In Atrium they must be derived index
   records whose source event IDs, input hashes, and synthesis version make them
   reproducible from layer 1 or layer 3.
2. Steal provenance links for synthesis. WHY: a concise episode or pattern is
   useful only if an agent can inspect the canonical evidence. Dense vectors can
   remain limited to this small synthesis layer while results point back to the
   archive.
3. Steal explicit scope dimensions and require them before ranking. WHY:
   provider, project, agent, conversation, and time filters should reduce the
   candidate set before the word, substring, or dense lane runs. This prevents
   cross-project memory leakage and improves ranking without ANN.
4. Steal idempotent background consolidation. WHY: Atrium can re-run episode
   synthesis safely after a model or prompt change if identity derives from
   source hashes plus synthesis version. Rebuildability becomes a tested
   property, not an operational hope.
5. Steal visible lifecycle metadata at read time. WHY: callers should be able to
   request current-only results or include superseded evidence. Keep that choice
   in the CLI core so every thin adapter behaves the same way.
6. Consider an optional rerank stage over a small candidate set. WHY: a local
   cross-encoder may improve precision after Atrium's measured lane routing. It
   must be benchmarked independently and must not replace the separately
   addressable word, substring, and dense results.

Reject Mem0's SQL memory store as a new source of truth. Atrium already has a
canonical archive and curated Brain notes; promoting extracted facts to an
independent truth would violate the disposable-index rule. Also reject raw
transcript writes through an `infer=False` escape hatch: Atrium must ingest only
the redacted canonical archive, never provider transcripts or a second copy
owned by layer 2.

## What to avoid

- Do not embed the raw corpus or adopt a vector database and ANN merely because
  Mem0 supports them. Atrium's measured design embeds only curated/synthesized
  content and brute-force scans that small set.
- Do not replace measured 70/30 weighted RRF and adaptive routing with an opaque
  managed fusion recipe. A blind lexical lane is already known to bury Atrium's
  dense signal.
- Do not blur word search and substring search into one keyword feature.
  Mem0's high-level retrieval abstraction does not address Atrium's measured
  `WAL` versus `wall...` failure.
- Do not make LLM extraction an irreversible ingest step. Model errors,
  omissions, and prompt drift require versioned outputs and complete replay.
- Do not import Platform-only behavior under an OSS label. Graph memory, richer
  filtering, temporal fusion, and Dream availability differ by product and plan.
- Do not default to accumulating both active and superseded facts in an agent's
  prompt. Preserve both in retrieval, but make the desired temporal view
  explicit.

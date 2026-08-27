# Graphiti study

Research snapshot: 2026-08-27. This note covers the open-source Graphiti
framework, not Zep's managed proprietary Context Graph Engine.

## What it is and how it works

Graphiti builds temporal context graphs for agents from a stream of text,
messages, or JSON. Its stored model has entity nodes, fact or relationship
edges, episodic nodes that preserve provenance, optional custom entity and edge
types, and higher-level communities. Facts have temporal validity windows, and
each derived item can trace back to the episode that produced it. [Graphiti repository](https://github.com/getzep/graphiti)

`add_episode` incrementally extracts entities and relationships with an LLM,
resolves them against the existing graph, deduplicates entities and facts, and
invalidates facts contradicted by new information. Graphiti distinguishes when
an episode was ingested from the reference time of the event it describes,
supporting bi-temporal history without full graph recomputation. [Extraction and resolution](https://github.com/getzep/graphiti/blob/main/graphiti_core/graphiti.py)

Graphiti uses a graph backend: Neo4j, FalkorDB, or Amazon Neptune; Kuzu is
deprecated. OpenAI is the default LLM and embedder, with other hosted and local
OpenAI-compatible options. Structured-output quality matters because malformed
LLM output can fail ingestion. [Requirements and providers](https://github.com/getzep/graphiti#installation)

Retrieval is recipe-based across facts, entities, episodes, and communities.
Current recipes combine BM25, cosine similarity, and sometimes graph BFS, then
offer RRF, maximal marginal relevance, cross-encoder, graph-distance, or
episode-mention reranking. Episode retrieval itself is full-text based. [Search recipes](https://github.com/getzep/graphiti/blob/main/graphiti_core/search/search_config_recipes.py)

`group_id` namespaces graph data. The MCP server exposes episode and triplet
writes, entity and fact searches, provenance lookup, saga summaries, community
construction, edge and episode deletion, and group clearing. Deleting an
episode cascade-deletes entities and facts that it alone created. [MCP operations](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md#available-tools)

Version 0.29.0 added a first-class saga abstraction and `summarize_saga`,
multi-episode batch extraction, separate timestamp resolution, and a major
search-pipeline restructuring. [Graphiti 0.29.0 release](https://github.com/getzep/graphiti/releases/tag/v0.29.0)

## Mechanisms it implements well

- Encode: incremental episode ingestion, LLM entity/fact extraction, custom
  ontologies, embeddings, and direct structured triplet insertion.
- Retrieve: BM25, cosine, graph traversal, temporal filters, configurable
  recipes, and multiple rerank strategies over distinct object types.
- Consolidate: entity resolution, community summaries, and saga summaries that
  roll up multiple ordered episodes.
- Forget: contradicted facts receive invalid validity windows; explicit episode
  deletion cascades only through facts and entities solely supported by it.
- Scope: `group_id`, entity and edge types, episode source, metadata, and
  temporal ranges constrain retrieval and maintenance.
- Dedupe: extracted nodes are deduplicated, then resolved against existing
  entities; extracted edges are resolved into new, duplicate, or invalidated
  facts.
- Rerank: RRF, MMR, cross-encoder, node-distance, and episode-mention options
  make candidate generation and final ordering separate choices.

Its strongest design is the combination of temporal invalidation and episode
provenance: a current fact can win retrieval while the old claim and the source
of each claim remain inspectable.

## What Atrium should steal

1. Steal bi-temporal metadata for derived claims. WHY: Atrium should distinguish
   source event time, ingest time, synthesis time, and the validity interval of
   a conclusion. That supports both current-state and historical queries without
   mutating canonical events.
2. Steal provenance edges from every synthesis to exact source events. WHY:
   episode summaries and curated-note matches must be auditable, and a rebuild
   can verify that every derivative still has canonical support.
3. Steal non-destructive contradiction handling. WHY: mark a derived claim as
   superseded and link its replacement rather than deleting it. Store these
   links only in the disposable index or regenerate them from versioned
   synthesis inputs.
4. Steal episode and saga boundaries as synthesis units. WHY: Atrium already
   needs smaller coherent episodes rather than whole sessions with topic jumps.
   A higher-level rollup can summarize related episodes, but it must preserve
   the membership list and synthesis version.
5. Steal typed, independently configurable candidate and rerank stages. WHY:
   Graphiti demonstrates that retrieval method and reranker need not be one
   opaque pipeline. Atrium should keep its word, substring, and dense lanes
   separately callable, then apply measured 70/30 RRF only when routing says
   fusion is appropriate.
6. Evaluate graph-distance or entity-overlap reranking as an optional lane.
   WHY: relational queries may benefit after lexical or dense candidate
   generation. Benchmark it on Atrium's corpus; do not introduce a graph
   database or change the default based on Graphiti's architecture alone.
7. Steal provenance-aware deletion semantics for index maintenance. WHY: when a
   canonical source disappears or changes hash, remove only derived records no
   longer supported, then rebuild affected synthesis. Never delete shared
   derivatives merely because one supporting event vanished.

Reject Graphiti's raw episodic store as ground truth inside Atrium. Layer 1
already owns the redacted, SHA-256-verified archive. Layer 2 should keep source
IDs, hashes, offsets, and rebuildable derivatives, not a second authoritative
copy of episode content. Also reject making a graph database a prerequisite:
it adds migrations, indexes, external services, and reconstruction cost without
evidence that Atrium's measured workload needs graph traversal.

## What to avoid

- Do not embed raw episodes or adopt ANN. Atrium's dense lane is deliberately
  limited to curated and synthesized content and scanned by brute-force cosine.
- Do not fuse BM25, cosine, and graph traversal for every query. Atrium has
  measured that a blind lane can suppress the only useful signal; routing must
  choose lanes before fusion.
- Do not collapse whole-word and substring retrieval into Graphiti's one
  full-text concept. Atrium's exact acronym failure requires separate lanes.
- Do not make LLM extraction, entity resolution, and timestamp inference an
  unversioned write path. Each can hallucinate or drift and must be replayable.
- Do not assume temporal invalidation automatically means current-only search.
  Make current versus historical views explicit in the CLI and verify filters
  in every adapter.
- Do not import ontology and community-building complexity before a labeled
  evaluation shows a gain over Atrium's simpler source, scope, and episode
  metadata.
- Do not expose dynamic graph queries directly through adapters. Graphiti's
  0.28.2 release fixed Cypher injection in search filters, illustrating the
  extra security surface created by a graph query layer.

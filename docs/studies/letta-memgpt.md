# Letta and MemGPT study

Research snapshot: 2026-08-27. The current system differs substantially from
the architecture described in older MemGPT and Letta V1 material, so this note
uses the current documentation and active repository.

## What it is and how it works

MemGPT introduced an operating-system analogy: an agent manages limited main
context and moves information to and from external memory through tool calls.
Letta is the product lineage built by the MemGPT authors. In 2026, the old
`letta-ai/letta` repository is a landing page, the V1 server is retired, and the
active harness, terminal UI, App Server, channels, and runtime live in
`letta-ai/letta-code`. [Current repository status](https://github.com/letta-ai/letta)
[Active Letta Code repository](https://github.com/letta-ai/letta-code)
[MemGPT paper](https://arxiv.org/abs/2310.08560)

The current long-term memory architecture is MemFS. Every agent owns a Git
repository projected as a normal filesystem checkout. Memories are Markdown
files with YAML frontmatter. Files under `system/` enter the system prompt on
every turn; other files stay out of context, while their file tree remains as a
navigation map. The agent reads, edits, commits, and, for cloud-backed agents,
pushes this repository. [MemFS](https://docs.letta.com/concepts/memfs)

MemFS has no semantic or vector index by default. Agents use ordinary file
search and reads. An optional MemFS Search mod adds keyword search, while
semantic and hybrid modes require QMD. Conversation-history search is a
separate subsystem: Cloud supports full-text, vector, and hybrid message search;
local backends currently provide full-text message search. [MemFS search](https://docs.letta.com/concepts/memfs#semantic-and-vector-search)

An agent is a persistent identity containing prompt/personality, MemFS memory,
model and tool configuration, and one or more conversations. Memory is shared
across that agent's conversations. Each agent has its own MemFS; organization-
owned shared-memory Git repositories provide files to multiple cloud agents.
[Stateful agents](https://docs.letta.com/concepts/stateful-agents)
[Shared memory](https://docs.letta.com/concepts/shared-memory)

Memory maintenance is agentic. `/remember` asks the agent to place a durable
lesson. Dreaming runs background subagents that review recent conversations and
update memory. `/doctor` audits placement, duplication, and prompt size.
Reorganization backs up the repository before splitting files, merging
duplicates, or restructuring the hierarchy.
[Memory and dreaming](https://docs.letta.com/configuration/memory)

## Mechanisms it implements well

- Encode: the agent selects durable information, places it in a named Markdown
  path, and commits the change; `/init` can bootstrap memory from a project.
- Retrieve: a small always-loaded `system/` tier, a visible file-tree routing
  tier, on-demand file reads, optional keyword/semantic search, and separate
  conversation-history search.
- Consolidate: background dreaming, optional second-agent review, `/doctor`,
  and backed-up hierarchy reorganization.
- Forget: explicit file edits or deletions remain recoverable through Git.
  Current docs do not describe an automatic decay or expiry policy for MemFS.
- Scope: per-agent memory across conversations; separate organization-owned
  repositories for deliberately shared knowledge.
- Dedupe: agent-driven audits and reorganization can merge duplicates, with Git
  preserving the pre-merge state.
- Rerank: no default MemFS reranker is documented. Optional search is separate
  from the always-loaded and path-routed tiers.

The strongest mechanism is the distinction between always-present identity and
rules, a cheap directory map, and deeper material loaded only when needed. Git
also makes every mutation inspectable and reversible.

## What Atrium should steal

1. Steal tiered context assembly, not agent-owned canonical memory. WHY: Atrium
   can inject a compact, frozen session-start snapshot, expose source-backed
   synthesis through search, and leave deeper evidence on demand. This controls
   prompt cost while retaining provenance.
2. Steal the visible navigation map. WHY: a compact inventory of projects,
   source types, time ranges, and synthesis topics can help an agent choose
   `--words`, `--substring`, or `--dense` before retrieval. This complements
   adaptive routing rather than hiding it.
3. Steal background consolidation with an isolated review stage. WHY: episode
   synthesis can run outside the active interaction and a second pass can check
   evidence coverage, duplication, and unsafe instructions before publication.
   Outputs must remain versioned, reproducible derivatives.
4. Steal audit and rollback ergonomics. WHY: an Atrium `doctor`-style command
   could report orphaned synthesis, duplicate derived records, prompt budget,
   missing provenance, and index/source parity. Recovery should rebuild the
   index, not synchronize or repair it as precious state.
5. Steal explicit private versus shared scope. WHY: provider-independent core
   records should declare project and audience boundaries, while adapters only
   translate requests. Sharing must be opt-in and visible at the CLI layer.
6. Steal the frozen-boundary idea for injection. WHY: prepare session-start
   context from completed prior work and do not mutate the prompt prefix during
   the session. This supports cache stability and prevents half-consolidated
   memory from appearing mid-run.

Reject MemFS itself as Atrium's memory authority. In Letta, the agent-owned Git
repository is durable memory and synchronizes across machines. In Atrium, layer
1 and layer 3 are the only durable authorities; layer 2 must rebuild locally and
must never sync its index. If a Git artifact is useful, it belongs in Brain or a
versioned source registry after human approval, not hidden inside the index.

## What to avoid

- Do not couple retrieval semantics to one agent identity or harness. Atrium's
  CLI core must remain agent-agnostic, with thin adapters for each client.
- Do not let an agent silently rewrite durable source material. Letta treats
  self-editing as learning; Atrium may only create reviewable proposals and
  derived records, never write layer 1 or layer 3.
- Do not use filenames and directory trees as the only retrieval system. They
  are useful routing hints but cannot replace measured word, substring, and
  dense recall.
- Do not sync a mutable layer-2 repository or index between machines. The
  canonical archive syncs; each Atrium installation rebuilds.
- Do not run consolidation without immutable evidence links, versioned prompts,
  and deterministic input boundaries. Git rollback alone does not make an LLM
  summary reproducible.
- Do not import the full harness surface, including identity, tools, channels,
  schedules, mods, and cloud runtime. Those are product capabilities, not
  retrieval mechanisms, and would erase Atrium's narrow responsibility.
- Do not describe retired V1 core-memory blocks and archival vector memory as
  the current default architecture. Current Letta uses MemFS for all agents.

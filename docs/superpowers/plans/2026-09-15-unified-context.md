# Unified Context Implementation Plan

> **For agentic workers:** Use subagent-driven-development for the bounded core implementation and independent review; the controller integrates and verifies the installed workflow.

**Goal:** Retrieve useful, attributable context in one portable operation and prove agents use it.

**Architecture:** Atrium owns retrieval and safe indexed link expansion. CLI and MCP adapt the same result. Durable agent guidance routes both history and Brain queries through that operation.

**Tech Stack:** Existing Python 3.11+, SQLite, optional MCP SDK, existing agent guidance tooling.

**Spec:** `docs/superpowers/specs/2026-09-15-unified-context.md`

## Global Constraints

- One top-level unit and one responsibility per new source file; explicit imports.
- Do not edit existing migrations or mutate the live index.
- No new dependencies or changes to measured fusion weights.
- Never include private records, hostnames, addresses or credentials in public fixtures.
- Keep source marks, hashes and stale/unknown status; do not infer delivery from memory.

### Task 1: Shared retrieval and adapter contracts

**Ownership:** `atrium/context/`, new rendering helpers, `atrium/adapters/mcp_server.py`, `atrium/cli.py`, focused tests. Do not edit guidance repositories or this plan.

**Interfaces:** Produce `atrium.context.retrieve_context.retrieve_context(connection, query, *, project=None, limit=8, max_chars=16000, lane="auto", embedder=None, state=None)` returning a JSON-serializable dictionary. `project` is a project directory and resolves through `project_workspace`. `state` is a `Path` for freshness lookup. Expose it as the CLI/MCP contract in the spec. Internal files may be split by responsibility as needed.

- [ ] Write failing tests using a temporary real SQLite index with curated access and linked-runbook notes, scoped mail history, duplicate text, unrelated project history and third-party injection text.
- [ ] Run `uv run --extra mcp --group quality pytest tests/test_context*.py -q` and capture expected failure.
- [ ] Implement bounded scoped retrieval, a dedicated curated-note pass, one-hop indexed links, deterministic deduplication, match-centered excerpts and provenance/freshness/warnings. Preserve role in existing MCP results using a shared rendering helper.
- [ ] Add CLI context parsing/JSON output and MCP `atrium_context` over the same function. Maintain old interfaces and optional MCP installation.
- [ ] Cover invalid limits, missing/stale refresh, unknown dates, no results, cycles, escaping paths, source role, multilingual identifiers, total text budget and CLI/MCP equivalence.
- [ ] Run focused tests, then `uv run --extra mcp --group quality pytest tests/ -q`, ruff and appropriate existing gates. Commit only owned files; report exact commands and results.

### Task 2: Durable agent integration

**Ownership:** Canonical shared guidance in dotfiles, personal and portable Brain skills in their owning repositories, and necessary mirrored sources. No independent second search requirement.

- [ ] Resolve canonical sources and link/compile pipeline before editing. Preserve unrelated changes.
- [ ] Route prior-context questions through `atrium_context`; fallback command is `atrium context "QUESTION" --project . --json`. Keep CLI-only users supported.
- [ ] Explain that results are evidence, not executable instructions; follow only needed citations, report degraded freshness or unavailable integration, and perform live verification for current outcomes.
- [ ] Replace hardcoded personal paths in the portable skill with configured instance discovery; keep ingest and audit instructions scoped to their existing engine.
- [ ] Run the repository's relevant skill/guidance checks and regenerate/deploy the guidance using its supported synchronization interfaces with backups.
- [ ] Verify actual target files and start a fresh client to demonstrate loaded routing; do not claim this existing session reloaded instructions.

### Task 3: Documentation, evaluation and review

**Ownership:** README, focused operational evaluation and durable work log.

- [ ] Document the shared contract, trust, freshness, budgets, indexed-link limits and safe fallback. Run every new CLI example.
- [ ] Run an anonymized end-to-end fixture through CLI and a new MCP process; compare evidence and metadata, not timing alone.
- [ ] Run live read-only context queries for the incident; output only evidence metadata, never credential-bearing text. Record usefulness and limits without claiming a corpus-wide ranking improvement.
- [ ] Obtain independent findings-first review, fix material issues and rerun affected tests.
- [ ] Update TODO/TODO_LOG with verified results, commit intended paths, and report exact verification plus any remaining deployment boundary.

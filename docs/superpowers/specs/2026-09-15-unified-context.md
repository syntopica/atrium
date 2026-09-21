# Unified context retrieval

## Approved outcome

A single agent-facing call retrieves relevant project history and curated knowledge,
follows useful indexed wiki links, and returns bounded evidence with provenance,
freshness and explicit limits. The same operation is available through MCP and a
JSON CLI. Retrieved history never establishes a present-day operational outcome.

## Contract

- Add `atrium_context(query, project=None, limit=8, max_chars=16000, lane="auto")`
  and `atrium context QUERY --project DIR --limit N --max-chars N --lane L --json`.
- Keep existing search/recall APIs compatible. Preserve `role` and an explicit
  trust classification in every MCP search and recall result.
- Combine project-scoped history with curated `role=note` records in the selected
  instance. Never widen to another project's raw conversation implicitly. Notes
  have no workspace today: they need a separate, visible curated retrieval pass.
- Keep measured search fusion and embedding choices unchanged. Return transparent
  retrieval steps and deduplicate repeated evidence. Follow only indexed curated
  wiki links, at most one hop, within the same evidence/count/character budgets.
- Return stable record IDs, source hashes, note paths where known, origin/trust,
  dates, truncation flags, route/scope, freshness and warnings. Missing or malformed
  configuration/index metadata is explicit; an empty result is not a healthy store.
- No arbitrary filesystem reads from retrieved links, credential retrieval,
  external execution, read-side database mutation, new model dependency or schema migration.
  Existing stores may add rebuildable secondary indexes through the explicit
  `prepare-context` command; canonical records must remain unchanged.
- Resolve instance state using existing Syntopica configuration. Work without
  machine-specific paths and without a configured Brain checkout; indexed notes
  remain the retrieval source, with their revision hash clearly labelled.
- Agent guidance and the Brain skill select this flow first, prefer resident MCP,
  use JSON CLI as fallback, and explicitly report degraded fallback. A manual wiki
  read is a bounded fallback for unresolved sources, not a second mandatory pass.

## Acceptance

An anonymized server-style fixture must retrieve both a project's mail-routing
history and a workspace-less access note, follow its runbook link, exclude another
project's history and third-party instructions, remove duplicate evidence, honor
budgets and require live verification before stating a message was delivered.
Test empty/stale/broken stores, cyclic and unsafe links, multilingual exact
identifiers, CLI/MCP parity and origin preservation. Verify installed CLI and a
fresh MCP process, then a fresh agent session with portable fixture guidance.

## Delivery boundaries

User approved implementation and testing on 2026-09-15. This is not authorization
to publish private data, send email, change server configuration or release a version.
Canonical guidance changes must be deployed and checked, not merely described.

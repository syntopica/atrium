# Unified context acceptance — 2026-09-15

## Result

The CLI and resident MCP now share one bounded retrieval operation. It combines
project history, workspace-less curated notes and one-hop indexed links, while
preserving origin, source revisions, dates, scope and explicit degradation.
Third-party records remain available only through explicit search, marked
untrusted. Every context response requires live verification of current outcomes.

## Repeatable checks

```bash
uv run --extra mcp --group quality pytest tests/ -q
uv run --extra mcp --group quality pytest tests/test_context_protocol.py -q
uv run --extra mcp --group quality baseline-py gate --json
uv lock --check
git diff --check
```

The full suite passed **236 tests** in 5.13 seconds. The protocol test starts a
real MCP subprocess and a separate CLI process against the same synthetic instance.
It verifies access information, scoped history, linked procedure, origin marks,
budget bounds and CLI/MCP evidence parity. Regression tests also cover folded
diacritics with original excerpt offsets and rejected links counting toward the
50-target cap. Independent review approved the final implementation.

The aggregate quality gate retains two pre-existing BPY001 structural findings:
`atrium/embed/model_repo.py` has no declaration, and
`atrium/ingest/decode_workspace_segment.py` has a second declaration. They remain
in `TODO.md`; the aggregate gate must not be reported as green.

## Full-index measurements

The first implementation exceeded a 90-second deadline on an operational query.
A materialized scoped-row filter alone still exceeded 60 seconds. Native sampling
identified SQLite record-page reads as the bottleneck. Two additive covering
indexes now make role/workspace filtering happen before retrieving record bodies.

`atrium prepare-context --json` prepared the selected existing store and reported
**1,399,794 records before and after**. It does not change canonical content or
existing migrations. Preparation can take several minutes on a large index;
read-only queries report missing preparation immediately instead of doing the
previous slow scan.

| Check | Observed elapsed time |
| --- | ---: |
| Installed CLI, automatic lanes | 10.301 s |
| New MCP process, first automatic query | 8.491 s |
| Same resident MCP, repeated automatic query | 6.109 s |
| Same resident MCP, focused lexical access query | 3.500 s |

All measured responses included scoped history and curated access notes, stayed
within the 8,000-character text budget and required live verification. The broader
query reported candidate saturation and an unresolved indexed link. Those warnings
remain visible; this is a small operational measurement, not a corpus-wide ranking
benchmark or a latency guarantee. Only metadata and evidence-presence booleans were
recorded; private note bodies and credentials were not exported.

## Installed guidance and fresh-client check

The canonical shared guidance and both provider targets now prefer `atrium_context`,
with structured CLI fallback. The portable Brain skill uses the configured instance
and avoids a second mandatory wiki search. Generated skill copies were checked for
hash parity against the canonical build.

The owning repositories were verified with:

```bash
# Agent control plane
pnpm run skills:compile
pnpm run check
pnpm run guidance:doctor -- --config ../dotfiles/agent-guidance --json
pnpm run guidance:sync -- --config ../dotfiles/agent-guidance --accept-published --json

# Host configuration
./scripts/check
```

The agent gate passed with a temporary executable wrapper for a pre-existing local
pnpm launcher that lacks a shebang. The direct launcher issue is recorded in that
repository's TODO. An initial guidance reconciliation timed out without applying
changes; the existing validator and atomic application API then applied the reviewed
canonical result with a rollback snapshot. The normal doctor returned no findings,
and the next normal sync confirmed convergence without running reconciliation.

A fresh, ephemeral Codex session used the actual installed global instructions and
Brain skill, with only a synthetic Atrium server enabled. The prompt asked about a
missing message without naming the routing tool or supplying the answer. Its event
stream contained exactly one completed `atrium_context` call. It recovered the
synthetic ORBIT-42 diagnostic profile, the remote-routing history and the linked
SMTP procedure. Its answer explicitly left the cause unproven because no current
transaction existed, and distinguished server acceptance from inbox placement.

The first isolated-client attempt did not expose the supplied MCP server and used
a manual fallback; it is not counted as a successful tool-routing test. Repeating
with the normal client configuration and per-run server overrides passed. Neither
run sent a message or contacted an operational mail service. Existing sessions need
to restart to discover new tools and reload instruction files.

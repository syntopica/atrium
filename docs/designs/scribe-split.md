# Split conversation capture out of syntopica/agents into syntopica/scribe

Status: revised 2026-10-11 after an adversarial review (Codex, read-only), every finding
accepted. Owner decisions: the new repository is `syntopica/scribe` (public); BRP (rules,
skills, plugins, hooks, workflow engine, library, machine) stays in `syntopica/agents`.

## Why

`syntopica/agents` holds two products with no shared domain:

1. BRP, the agent control plane.
2. Layer 1 of the memory stack: provider discovery and read-only capture, the canonical
   conversation schema, redaction, the archive (v1 JSONL and the v2 segment store), import,
   export, render and doctor.

Layer 1 is consumed by Atrium (layer 2) and exchanged between machines by dotfiles. Its
release cadence, tests and audience are those of the memory stack, not of BRP. Archive v2
stage 3 and source block provenance for tool results (Atrium TODO F3) are layer-1 work and
should land in the repository that will own them.

## What moves

Inventory measured on 2026-10-11 (`rg --files`, import search plus CodeGraph):

- `scripts/lib/conversations/`: **233 files**, 22 `*_TEST.ts`, including nested fixtures,
  validators, types and formatters. Copy the whole tree, not a list.
- `scripts/commands/conversations*.ts` (9) and `scripts/bin/run-conversations-*.ts` (9).
- Four outward imports, re-created as four scribe-owned one-unit files with their own tests:
  `flagValue.ts`, `flagValues.ts`, `resolveSecondaryDesktopDir.ts`,
  `reportUnexpectedFailure.ts`. No shared package.
- Package scripts `conversations:{doctor,export,capture,migrate-segments,verify-segments,
  benchmark-segments,import,rewrite,render,test}`, kept as wrappers over a new `scribe` CLI.
- The TypeScript, ESLint (the `conversation-lib` boundary), tsconfig, formatter, dependency
  and `eslint-suppressions.json` entries those files need; a committed `pnpm-lock.yaml`
  under the pinned pnpm and Node.
- Docs: `docs/architecture/conversation-ownership.md`, `docs/adr/0002-canonical-
  conversation-transport.md`, `docs/runbooks/conversation-transport.md`, the README and
  AGENTS smoke commands for conversations.
- Backlog: agents TODO sections "Conversations export" and "Conversation capture gaps",
  moved with provenance, pointers left where work stays cross-project.

Executable layout is load-bearing: `runConversationCapturePass.ts` resolves
`scripts/bin/run-conversations-capture.ts` from `import.meta.url`, so keep the
`scripts/{lib,commands,bin}` relationship and exercise the benchmark after the move.

Stays in agents: `codex:*` (`codex-state`, depends on `library` and `platform-health`) and
`library:observe*`. `library:observe` reads provider transcripts directly, which the
ownership document forbids; filed as a follow-up to consume scribe output.

No production module outside the move set imports `scripts/lib/conversations` (two
independent sources agree), but non-import references exist: package gates, ESLint,
suppressions, AGENTS, README, runbook, ADR, TODO, and external callers. "No import" is not
a deletion gate.

History: `git log --all -- scripts/lib/conversations` shows real conversation commits after
the squash (`416b93e1`, `ffac2add`, later fixes). Preserve it with `git filter-repo
--path ... ` into the new repository, so blame survives; the first new commit names the
agents commit it was cut from.

## Compatibility during the move

Unchanged on purpose until v2 cutover:

- wire format: the `rocket-agents-conversation-export` header, event-id derivation and
  timestamp normalisation that Atrium's tests encode;
- environment variables `ROCKET_AGENTS_HOST`, `ROCKET_AGENTS_ARCHIVE_LOCK_WAIT_MS`,
  `CLAUDE_SECONDARY_DESKTOP_DIR`;
- both locks: the outer `~/.local/state/rocket-agents/archive.lock` (dotfiles wrappers) and
  the library's own `<archive>.write-lock` (`withArchiveWriteLock.ts`, also taken by the v2
  publisher); the state directory `~/.local/state/rocket-agents/conversations`;
- the v1 archive `<instance>/conversations/archive.jsonl` and transfer files.

Export does not take the outer lock, so the shared locks alone do not make a two-checkout
window safe. While both implementations exist on a machine: refresh and sync booted out
(launchd) for the switch, and nothing runs capture or import from the old checkout after the
new one has run once.

## Callers to repoint

- dotfiles `bin/atrium/atrium-refresh`: `npx tsx scripts/bin/...` in the agents checkout;
  both the working directory and the entry-point paths change (or it calls `scribe`).
- dotfiles `bin/sync-conversations`: local half honours `ROCKET_AGENTS_CHECKOUT`, the remote
  halves hardcode agents independently.
- dotfiles `bin/sync-all-safe`: peer detection skips a peer without an agents checkout,
  which would silently drop a peer that has scribe only.
- syntopica: `components.py`, `engine_repositories.py`, `run_doctor.py`, generated config
  tests (`test_build_config_document.py`), onboarding commands and `AGENTS.md`. Decision
  needed: selecting Atrium installs scribe alone, or scribe and agents. Proposed: scribe
  alone; agents only when BRP is selected.
- Atrium docs.

## Phases

1. Freeze scope and the archive contract; inventory the 233 files, docs, suppressions,
   dependencies, scripts and commits.
2. Create `syntopica/scribe` with the full tree (history via filter-repo), the four owned
   helpers, lockfile, the `scribe` CLI with `--help`, lint, type-check, tests, CI and a
   gitleaks/privacy scan. Gate: `pnpm install --frozen-lockfile`, type-check, lint,
   `pnpm run conversations:test` (same count as agents), `scribe --help`, `scribe doctor`,
   the benchmark's child-process path.
3. Parity from frozen inputs, never two live exports: run v1 export over a fixed fixture or
   frozen snapshot from both checkouts and compare stable record ids, canonical record
   hashes, counts, skipped-source inventories and redaction summaries (not whole files:
   `createdAt` differs). For v2, migrate a temporary copy of the v1 archive and run
   `conversations:verify-segments -- --root <temp-root>` in both, comparing generation and
   fragment digests. Run Atrium's ingest and contract tests against scribe output.
4. Prepare both machines: clone scribe, `pnpm install`, inspect the actual checkout, Node/pnpm,
   archive and state paths, symlinks, free space and installed dotfiles scripts; run scribe
   locally on each; existing callers stay live.
5. Repoint, one machine at a time with refresh and sync booted out: refresh, both sync halves,
   peer detection, wrapper docs, syntopica components and tests. Verify: refresh log shows
   scribe, `sync-conversations` dry run in both directions, import totals and Atrium ingest
   unchanged. Only then the peer.
6. Remove the moved code, scripts, suppressions and docs from agents, adjust its quality
   gate, leave pointers. Gate: agents `check:all` green; executable references searched
   separately from historical prose.
7. Later releases in scribe: v2 stage 3 (erasure, transport, the pending slice handed to
   `atrium ingest --partial`, scheduler and hook freeze, cutover) with its own data-location
   and rollback plan; tool-result block provenance; versioned archive-contract fixtures that
   Atrium's tests consume.

## Open decision

- Syntopica onboarding: Atrium pulls scribe alone (proposed) or scribe plus agents.

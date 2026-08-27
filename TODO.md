# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-08-27. History coverage: Partial —
> Atrium was designed and built inside the `~/p/mempalace` project history
> (session `a88ac62e`, 2026-08-25 to 2026-08-27, plus one Codex review
> rollout); that history is fully parsed here. The older mempalace sessions
> cover the fork itself and are consolidated in `~/p/mempalace/TODO.md`, not
> reparsed here.
>
> States: `[ ]` pending · `[~]` partial or unverified · `[!]` blocked · `[x]`
> verified complete · `[-]` obsolete or superseded. Closed work moves to
> `TODO_LOG.md`.

## Retrieval

- [ ] Dense-over-raw stays an explicit reserve lane: even with an oracle
  embedder the zero-lexical-overlap class recovers only 3 of 25 from synthesis
  alone. "No ANN" is not approved until the reserve lane is measured at full
  corpus scale.

## Ingest / Store

- [!] Codex source cannot be exported: `conversations:export --source codex`
  aborts the whole source because two rollouts exceed the exporter's 64 MiB
  limit (2026-08-19T21-06-36, 2026-08-26T13-41-24) — 4,345 exportable rollouts
  held hostage by 2. Smallest unblock: fix the rocket-agents exporter to skip
  oversized files with a warning (filed in `~/p/rocket-agents/TODO.md`;
  needs authorization to change that repo).
- [~] Materialize the full canonical archive: claude-code ingested 2026-08-27
  (566 MB export, 4,734 conversations -> 442,447 records, 4m40s, 1.8 GB
  index); cursor/opencode/openclaw/pi export+ingest running. Remaining:
  record final per-provider numbers, decide a durable location for the
  canonical archive files (today they live in a session scratchpad), and the
  codex source above.

## Synthesis

- [ ] Episode-level synthesis is the heart of the system, not phase 2: dense
  vectors cover only synthesized content, so synthesis quality *is* semantic
  search quality. Measured: 69.3% of sessions contain at least one topic jump,
  so the unit is the episode (cut on human turns + topic change), not the
  session file; 8.3% of sessions exceed 100k tokens (max 5.49M), so the long
  tail needs map-reduce. One-time cost for 8,570 sessions measured at $22-104.
  Derived episodes go to a versioned registry of Atrium's own; only
  user-approved notes are proposed to brain (a tray, not a dump).
- [ ] Session-start injection: frozen-snapshot discipline (write at session
  close, inject at the *next* session start to preserve prefix cache), budget
  ~170-900 tokens — the mechanism users remember as valuable from mempalace;
  the synthesis behind it never existed there (checkpoints were literal
  message tails).

## Measurement

- [!] Hand-labeled acceptance set — blocks the measurement phase. The 365/389
  question-answer pairs used so far are machine-extracted and not valid for
  production decisions ("better than mempalace" needs a number). Smallest
  unblock: the user labels a stratified question set over the corpus, or
  approves a labeling protocol.

## Integrations

- [ ] Thin adapters over the CLI core: MCP server and per-agent hooks.
  Integrating a future agent must be an adapter, never an engine change.
- [ ] Early spike (deliberately promoted from phase 3): ChatGPT and Grok have
  no local transcript — design the remote-export adapter family before the
  local-file assumption hardens.
- [ ] Connect the captured-but-never-indexed sources end to end once the
  archive is materialized: cursor 101 artifacts, opencode 358, openclaw 13,
  trae 12, windsurf 4, pi 4 — none ever reached the old index.

## Security

- [ ] Mark untrusted-origin content and never auto-inject it: brain stores
  saved web articles (third-party text), and a retrieved instruction inside one
  can steer a tool-bearing agent. Tag origin at ingest; requires no restriction
  on the user's own access. (Accepted Codex round-1 warning.)

## Self-improvement

- [ ] Query log, gap detection, and brain proposals — with the durable-state
  contradiction resolved first: layer 2 must stay disposable, so synthesis,
  query log and proposal state either live in brain or in an explicitly
  backed-up sidecar. As designed today a rebuild would erase them.
- [ ] Studies directory: one note per memory system analyzed (which mechanism
  to adopt and why). Pending second research round: mem0, Letta/MemGPT,
  Graphiti — the systems `~/p/brain/topics/agent-memory.md` does not cover in
  depth.

## Cross-project

- [ ] `rocket-agents`: canonical event IDs are conversation-local in practice —
  `conversationEventFromRecord.ts:20` derives them from `event_index + text`
  with no conversation identity, and real cross-conversation collisions were
  measured (OpenCode, Cursor). Atrium works around it with
  `sha256(conversation_id, event_id)`; the canonical contract should carry the
  identity itself. Also: the Windsurf exporter emits 0 conversations from 4
  database artifacts. Filed in `~/p/rocket-agents/TODO.md`.
- [ ] `mempalace` fork: the live palace embeds with the English-only default
  model over a ~77% Spanish corpus; switching to `embeddinggemma` (same 384
  dims, config-only) nearly doubles dense quality (R@10 40.8% -> 70.4%) at
  ~36 h CPU re-embed. Decision pending: worth doing while Atrium replaces it?
  Filed in `~/p/mempalace/TODO.md`.

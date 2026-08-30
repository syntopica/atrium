# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-08-27. History coverage: Partial —
> Atrium was designed and built inside the `~/p/memstore` project history
> (session `a88ac62e`, 2026-08-25 to 2026-08-27, plus one Codex review
> rollout); that history is fully parsed here. The older memstore sessions
> cover the fork itself and are consolidated in `~/p/memstore/TODO.md`, not
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

- [ ] Codex source unblocked 2026-08-27: rocket-agents gained
  `--allow-partial` (commit `bfa54ec` there) and the full codex export landed
  — 4,356 conversations -> 21,219 records ingested, manifest declares
  `complete:false` with the two >64 MiB rollouts listed. Remaining here: once
  rocket-agents ships the streaming exporter (its TODO), re-export codex
  complete and re-ingest so those two rollouts join the index.
- [ ] Multi-machine archive sync: the durable archive now lives at
  `~/.local/share/rocket-agents/conversations/archive.jsonl` (decided in the
  2026-08-27 consult; XDG data, 0600/0700, import-verified). Remaining:
  point the dotfiles `sync-conversations` transport at `.local/share`
  (it currently syncs `.local/state`) and prove convergence on the second
  machine with the dry-run-reports-no-changes check. Cross-project: dotfiles.

## Synthesis

- [ ] Episode-level synthesis is the heart of the system, not phase 2: dense
  vectors cover only synthesized content, so synthesis quality *is* semantic
  search quality. Measured: 69.3% of sessions contain at least one topic jump,
  so the unit is the episode (cut on human turns + topic change), not the
  session file; 8.3% of sessions exceed 100k tokens (max 5.49M), so the long
  tail needs map-reduce. One-time cost for 8,570 sessions measured at $22-104.
  **Built 2026-08-28** (commit `6263938`): cutter, registry, Max-lane
  producer, `synthesize` + `ingest-synthesis` CLI; verified live; first
  tranche done on the Max lane (383 episodes, 4.7M input tokens -- measured
  cost that triggered the routing change below). Bulk now runs on the agy
  drip loop (`~/.local/share/atrium/synthesis/drip-loop.sh`, quota-aware
  via CodexBar; log `run.log`, passes logged in `drip.log`); a pass aborts
  at the Gemini quota wall instead of grinding failures (commit `cf9a320`).
  2026-08-28 22:50: 13,309 records in registry, 11,835 embedded; a stale
  duplicate run (workers 6, pre-drip orphan) was killed -- it was doubling
  quota burn. **2026-08-30 audit found the drip had produced nothing for a
  day and a quarter, and three defects behind it, all fixed the same day:**
  * The on-disk `active-recipe.json` listed only
    `["codex-cli-default","claude-sonnet-5"]`, so the whole
    `gemini-3.7-flash-medium` population -- 3,686 episodes across 580
    conversations, a quarter of everything synthesized -- was produced and
    then dropped at ingest. Adding it took served coverage from 2,029 to
    **2,609 conversations** and 11,835 to **14,653 records**, with no calls.
  * `drip-quota.py` read only the `Gemini 5-hour` window. That window reports
    `usedPercent 0` with `usageKnown: false` while `Gemini weekly` sits at
    100%, so the probe answered "go now", every pass aborted on its first
    call, and the loop ground for ~18 h logging `failed=10790` with zero
    output. It now reads every Gemini window, treats `usageKnown: false` as
    no evidence of headroom rather than as headroom, and sleeps to the
    furthest reset (cap raised 4 h -> 24 h, since the weekly wall is ~14 h out).
  * The loop had died outright (no process since 08:12) and nothing restarted
    it. It now takes a `mkdir` lock with a stale-pid check -- macOS has no
    `flock(1)` -- so a second start exits instead of doubling the quota burn
    the way the 2026-08-28 orphan did.
  Measured coverage after the fixes: **2,609 of 11,028 archived conversations
  (23.7%)**; 8,419 conversations still unsynthesized. One day of agy work on
  2026-08-28 (13,966 records) spent an entire Google AI Pro *weekly* quota,
  so the remaining corpus is several weekly cycles on that lane alone.
  Remaining: let the drip finish, re-run `ingest-synthesis` + `embed`
  periodically, and spot-check quality with Codex as evaluator. **Design pinned in the 2026-08-27 two-agent
  consult, one amendment by operator directive:**
  * Producer, second amendment (operator, 2026-08-28): the Codex CLI's own
    quota (`--producer codex`, default) after the Max lane measured 4.7M
    input tokens for 383 episodes; the Max lane stays as `--producer max`.
    Populations never mix: the model id is in the job key and the
    active-recipe manifest picks exactly one record per episode at ingest.
    The one-producer-population and codex-as-evaluator clauses of the
    original consult are amended by these operator directives.
  * Segmentation: `episode-texttiling-v1` — turn blocks per human message;
    hard cuts at reset markers; TF-IDF TextTiling over human turns only
    (bilingual ES/EN stopwords), three-turn windows, valley depth > session
    median + 1 MAD, >=2 human turns between cuts; 32k-token ceiling with one
    pinned tokenizer; oversized coherent episodes map-reduce mechanically and
    the map chunks are never retrieval episodes. Deterministic, no LLM and no
    embeddings in the cutter.
  * Storage: immutable content-addressed registry at
    `~/.local/share/atrium/synthesis/` with an atomic active-recipe manifest;
    one designated synthesis writer, other machines consume; synced by the
    dotfiles transport, never the SQLite index.
  * Every record carries the full recipe (archive hashes, episode id +
    ordered event hashes, segmentation fingerprint, provider + exact model
    snapshot, prompt sha256, output schema version, inference params,
    generator version, parent map ids, output sha256). Job key = hash of all
    inputs minus output; same job key with different output hashes is a hard
    divergence error, never resolved by timestamps.
  Only user-approved notes are proposed to brain (a tray, not a dump).
- [ ] Session-start injection: frozen-snapshot discipline (write at session
  close, inject at the *next* session start to preserve prefix cache), budget
  ~170-900 tokens — the mechanism users remember as valuable from memstore;
  the synthesis behind it never existed there (checkpoints were literal
  message tails).

## Cutover from memstore

- [x] **Freshness automated 2026-08-30.** `~/.local/bin/atrium-refresh` runs
  export -> import -> ingest -> ingest-synthesis -> embed, under
  `~/.local/bin/atrium-lock` (a real `fcntl.flock` held across `execvp`; macOS
  has no `flock(1)`, and the `mkdir` + stale-pid pattern it replaced let two
  contenders both judge one lock stale). Two triggers, per operator directive:
  the hourly `com.cristian.atrium-refresh` LaunchAgent and the `Stop` hook
  `~/.claude/hooks/atrium-refresh-on-stop.sh`. The first live run showed the
  gap was far worse than three days: **the archive went from 11,164 to 23,449
  conversations** (`added: 12285`), and the index from 553,083 to 614,359
  records -- `codex` alone 21,219 -> 57,603. Only the newest archive backup is
  kept; the importer writes a full 2.6 GB copy on every apply.
- [x] **Read-side adapters shipped 2026-08-30** (`d917a35`). `atrium recall`
  renders the project's newest synthesized episodes in ~1.2 s with no embedder;
  `~/.claude/hooks/atrium-recall.sh` replaced the memstore recall hook in
  `SessionStart` and was verified to load in *both* profiles by asking the
  the work organization profile to quote the injected block back. The MCP server
  (`atrium.adapters.mcp_server`, optional `mcp` extra, registered as `atrium` in
  both `.claude.json`) keeps one resident `Embedder`: measured over the
  protocol, the first search costs 20.7 s and the next 2.7 s.
  Deliberate divergence from the frozen-snapshot design: `atrium recall` is
  deterministic given the index and cheap enough to run live, so a snapshot
  file would add a staleness window and a writer for no measured gain.
  Revisit if recall ever needs the dense lane.
- [x] **Synthesis records carry their conversation's workspace** (`28e2c7b`).
  14,630 of 14,653 now do; the 23 without are conversations the exporter could
  not place, and they stay unscoped rather than borrow a neighbour's.
- [ ] Retire memstore. Everything that blocked it is done; what remains is the
  operator's call and the reversible steps: unload
  `com.memstore.daemon/.watchdog/.retention/.codex-mine`, remove the plugin's
  MCP registration and skills, then reclaim `~/.memstore`. Two things to
  settle first:
  * `~/.memstore/palace/knowledge_graph.sqlite3` (untouched since 2026-06-09)
    holds 2,897 entities and 1,912 triples -- the only memstore content not
    reconstructible from the archive. The *live* KG is empty (0/0), as are the
    active artifact and event stores, so nothing else there is load-bearing.
    Decide whether any of those 2,897 belong in brain before deleting.
  * Keep `~/.memstore` read-only until a few sessions have run on atrium
    recall. 118 GB, of which ~87 GB is dead rebuild snapshots and a 14 GB
    `chroma.sqlite3.pre-wal-20260825`; the live palace is 31 GB against
    atrium's 3.3 GB index.

- [-] Freshness blocker as originally filed:
  `~/.local/share/rocket-agents/conversations/archive.jsonl` was last written
  2026-08-27 23:47 and *nothing* refreshes it: no LaunchAgent, no crontab
  entry runs `run-conversations-export`. The only scheduled rocket-agents job
  is `com.cristian.library-loop` (a learning report, and it has been logging
  `skipped: a report younger than 7 day(s) exists` for weeks). memstore
  captures live on Stop; atrium's corpus is frozen until a human exports.
  Until this is automated, switching memstore off loses memory. Chain is
  `run-conversations-export --output <slice>` ->
  `run-conversations-import --input <slice> --archive <archive> --apply` ->
  `atrium ingest` -> `atrium embed`. Operator directive 2026-08-30: build
  *both* a periodic LaunchAgent and a session-Stop hook.
- [-] Superseded by the entries above. Read-side adapters (supersedes the generic "thin adapters" item below
  for the cutover). Two pieces, per the 2026-08-30 two-agent consult:
  * A long-lived stdio MCP server exposing `atrium_search(query, limit, lane,
    workspace?)` that calls the retrieval functions directly and keeps one
    lazy `Embedder`. The measured 7 s of `atrium search` is model load, paid
    per subprocess; a resident server pays it once. It must **not** parse CLI
    output -- `cli.py:393` truncates text to 200 chars for humans. Extract a
    shared function returning whole `Hit` objects.
  * Session-start injection as a frozen snapshot written at session close and
    injected at the *next* start (see the Synthesis section), so the hook
    only reads a file and the prefix cache survives.
  Then rewire `~/.claude/hooks/recall.sh`, the MCP registration and the
  recall skill, and verify in a fresh session before disabling memstore.
- [-] Superseded by the entries above. **Synthesis records carry no workspace, so project-scoped recall cannot
  reach them.** `to_synthesis_records.py:38` sets `workspace=None`; 0 of the
  indexed synthesis records have one, against 466k of 550k raw records that
  do. The memstore hook being replaced is wing-scoped (project folder name),
  so this blocks parity on the read side. No re-synthesis needed: the registry
  record carries `conversation_id` and that conversation is already indexed
  with its workspace -- resolve it at ingest.
- [-] Folded into the retirement entry above. memstore write side, measured 2026-08-30 -- smaller than assumed:
  knowledge graph, artifacts and events are **not** load-bearing. The live
  `~/.memstore/knowledge_graph.sqlite3` holds 0 entities and 0 triples, and
  the active logstream holds 0 artifacts and 0 events. Only checkpoints and
  the diary are in use (3,269 diary drawers), and those are literal message
  tails, which the frozen snapshot replaces properly rather than ports.
  One exception before any deletion: `~/.memstore/palace/knowledge_graph.sqlite3`
  (untouched since 2026-06-09) holds 2,897 entities and 1,912 triples -- the
  only memstore content not reconstructible from the archive. Decide whether
  any of it belongs in brain before retiring the store.
- [-] Folded into the retirement entry above. Reclaim: `~/.memstore` is 118 GB, of which ~87 GB is dead rebuild
  snapshots (`palace.pre-rebuild-20260804/-20260820/-20260824`,
  `palace.backup-20260825-purge`, `palace.pre-codeprune`, `palace.pre-mdprune`)
  plus a 14 GB `chroma.sqlite3.pre-wal-20260825`. The live palace is 31 GB;
  atrium's whole index is 3.3 GB. Do not delete until the cutover is verified.

## Measurement

- [!] Hand-labeled acceptance set — blocks the measurement phase. The 365/389
  question-answer pairs used so far are machine-extracted and not valid for
  production decisions ("better than memstore" needs a number). Smallest
  unblock: the user labels a stratified question set over the corpus, or
  approves a labeling protocol.

## Integrations

- [ ] Thin adapters over the CLI core: MCP server and per-agent hooks.
  Integrating a future agent must be an adapter, never an engine change.
- [ ] Early spike (deliberately promoted from phase 3): ChatGPT and Grok have
  no local transcript — design the remote-export adapter family before the
  local-file assumption hardens.
- [!] Windsurf and Trae remain unindexable at layer 1: the Windsurf exporter
  emits 0 conversations from its 4 database artifacts, and the Trae exporter
  emits VS Code workspace metadata instead of dialogue. Both filed in
  `~/p/rocket-agents/TODO.md`; smallest unblock is fixing those exporters
  (needs authorization to change that repo).

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

## Cross-project

- [ ] `rocket-agents`: canonical event IDs are conversation-local in practice —
  `conversationEventFromRecord.ts:20` derives them from `event_index + text`
  with no conversation identity, and real cross-conversation collisions were
  measured (OpenCode, Cursor). Atrium works around it with
  `sha256(conversation_id, event_id)`; the canonical contract should carry the
  identity itself. Also: the Windsurf exporter emits 0 conversations from 4
  database artifacts. Filed in `~/p/rocket-agents/TODO.md`.
- [ ] `memstore` fork: the live palace embeds with the English-only default
  model over a ~77% Spanish corpus; switching to `embeddinggemma` (same 384
  dims, config-only) nearly doubles dense quality (R@10 40.8% -> 70.4%) at
  ~36 h CPU re-embed. Decision pending: worth doing while Atrium replaces it?
  Filed in `~/p/memstore/TODO.md`.

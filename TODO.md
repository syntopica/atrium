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

- [!] Dense-over-raw stays an explicit reserve lane: even with an oracle
  embedder the zero-lexical-overlap class recovers only 3 of 25 from synthesis
  alone. "No ANN" is not approved until the reserve lane is measured at full
  corpus scale. Blocked by the same condition as the Measurement item below
  (2026-09-01): the only question set is machine-extracted, and this item
  exists precisely to justify a production decision ("no ANN"), which that set
  cannot do. Smallest unblock: the hand-labeled set, then the measurement is
  hours of embed CPU plus the existing eval harness.

## Ingest / Store

- [ ] Codex source unblocked 2026-08-27: rocket-agents gained
  `--allow-partial` (commit `bfa54ec` there) and the full codex export landed
  — 4,356 conversations -> 21,219 records ingested, manifest declares
  `complete:false` with the two >64 MiB rollouts listed. Remaining here: once
  rocket-agents ships the streaming exporter (its TODO), re-export codex
  complete and re-ingest so those two rollouts join the index.
- [~] **The archive's shape will not scale.** Specification agreed 2026-08-31
  with codex over three review rounds and kept at
  `docs/designs/conversation-archive-v2.md`: append-only journal of immutable
  content-addressed batches, observed-remove tombstones, set-reducer
  materialization, threshold compaction publishing a snapshot behind a
  compare-and-swapped `current.json`, a disposable per-writer cursor for
  incremental Atrium ingest, and an incremental capture cache. Measured
  baseline it has to beat, on this machine: one conversation costs 132.36 s and
  ~10.3 GB of archive I/O to publish, while a full capture costs 226.91 s and
  2.78 GB -- capture is the larger term, which the first design missed.
  Implementation is not started; it collides with an in-flight
  `CONVERSATION_SCHEMA_VERSION` 1 -> 2 change in rocket-agents that alters event
  id derivation, and the two migrations should be one verified pass over the
  archive rather than two. Original entry below.
- [ ] One JSONL rewritten in full on
  every import: 2.6 GB -> 3.36 GB in a day, and the 2026-08-31 recovery import
  took roughly 45 minutes to add 3,008 conversations. With an hourly refresh
  that is O(corpus) write amplification per hour to append a handful of
  conversations, and it gets worse monotonically. The archive is meant to hold
  everything forever, so the format has to stop being rewritten whole --
  segment by period or by source, or make append the normal path and the full
  rewrite a compaction. Cross-project: rocket-agents.
- [ ] **Whole conversations that have never entered the archive at all.** The
  codex export declares `complete:false` and skips two rollouts over 64 MiB
  outright; the Windsurf and Trae exporters emit zero conversations; ChatGPT
  and Grok leave no local transcript, so nothing has ever been captured from
  them. Each is filed separately below and in `~/p/rocket-agents/TODO.md`, but
  together they are the answer to "is the archive complete", and today the
  answer is no.

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
  Coverage after the fixes was 2,609 of 11,028 archived conversations (23.7%).
  **Re-measured 2026-09-01: 3,007 of 30,318 (9.9%)** — the numerator grew by
  398 while the denominator nearly tripled, because the memstore recovery and
  the Mac mini capture added conversations far faster than a quota-walled drip
  can synthesize them. Coverage is now falling, not rising, and the drip has
  been sleeping against the weekly Gemini wall since 2026-08-31 23:22. One day
  of agy work on 2026-08-28 (13,966 records) spent an entire Google AI Pro
  *weekly* quota, so the remaining corpus is many weekly cycles on that lane
  alone. Decide whether that lane can ever catch up, or whether coverage has to
  be bought differently (a second producer, a cheaper model, or synthesizing
  only what recall actually reaches for).
  **2026-09-01: the producer moved off the walled Gemini lane.** Benched four
  Codex configurations on three real unsynthesized episodes with a blind
  fourth-model judge (`docs/studies/synthesis-producer-bench.md`). The result
  inverts the obvious economy: dropping `gpt-5.6-sol` from high to low
  reasoning effort made it **fabricate** — three claims unsupported by the
  transcript across two episodes — while the smaller `gpt-5.6-terra` at low
  effort produced none and ran 2.2x faster than the account default. Bulk now
  runs `--producer codex --model gpt-5.6-terra --effort low`; the population
  `gpt-5.6-terra-low` is appended last in `active-recipe.json`, so it serves
  only episodes nothing else covers and never outranks paid-for output.
  Measured throughput: ~2.6 s per episode at 4 workers.
  **The scale is the open question, not the lane.** ~150,000 episodes remain
  (5.5 per conversation, measured over 300), which is ~108 hours of continuous
  running at 4 workers, and 84% of the corpus is the two most recent months, so
  there is no cheap prioritization escape — the recent work *is* the bulk.
  Decide the budget: run it down over days, raise worker count, or accept
  partial coverage as policy.
  **The double-payment already happened once, and it is measurable.** Audited
  2026-09-01 over all 17,159 episodes in the registry: 383 of them hold records
  from two populations, and the pair is always `claude-sonnet-5` +
  `codex-cli-default` — that is the entire Max-lane tranche, 4.7M input tokens,
  re-synthesized by codex after the 2026-08-28 producer switch. It is also
  exactly why `claude-sonnet-5` serves nothing today: codex outranks it on
  every episode it holds. The new `gpt-5.6-terra-low` population contributed
  **zero** duplicates, so the `done_episodes` guard does hold within a single
  producer at a time.
  **Two producers must not run at once.** The agy drip loop is still installed
  and alive, sleeping to its next Gemini reset (observed 2026-09-01 04:05,
  sleeping 15,355 s). `done_episodes` is read once at pass start, so a codex
  pass and a drip pass overlapping will both pick up the same pending episodes
  and pay for each of them twice, in two populations — the failure the
  one-population rule exists to prevent. Before any long codex run, stop the
  drip (or gate it on the same lock) rather than trusting the two schedules not
  to meet.
  Remaining: let the pass run, re-run `ingest-synthesis` + `embed`
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

## Observability

- [ ] **A second writer blocks silently, with no output and no error.** Running
  `atrium embed` by hand while the hourly refresh was inside its own
  `ingest-synthesis` left it at 0% CPU for twelve minutes: no vectors written,
  nothing printed, no timeout — indistinguishable from a hung process or a slow
  model load, and diagnosable only by finding the other process. `busy_timeout`
  is 30 s, so something is waiting well past it. Either the long-running
  commands should say "waiting for another writer" the moment they queue, or
  the CLI should refuse a second concurrent writer outright and say which
  process holds it. Discovered 2026-09-01 while babysitting the codex lane.

> Filed 2026-08-31, from the memstore retirement. Every defect that session
> found had been running silently for days, and none of them were subtle --
> they were invisible because nothing reported the right number.


- [ ] **The dotfiles auto-sync manufactures conflicts and leaves them.**
  `com.cristian.sync-all-safe` merges the two machines and commits, but a
  conflict stops it mid-merge and nothing resolves or reports it. One sat
  unresolved from 2026-08-29 until it was found by accident on 2026-08-30, and
  a second appeared within a day of that -- both in `agent-guidance/shared.md`
  and `claude/settings.json`, which are exactly the files that carry agent
  guidance and confirmation rules. A repo left with `UU` paths also blocks
  every later commit, so an unnoticed conflict silently stops the sync
  entirely. It needs to either resolve deterministically, or fail loudly
  enough that someone looks. Cross-project: dotfiles.

## Measurement

- [!] Hand-labeled acceptance set — blocks the measurement phase. The 365/389
  question-answer pairs used so far are machine-extracted and not valid for
  production decisions ("better than memstore" needs a number). Smallest
  unblock: the user labels a stratified question set over the corpus, or
  approves a labeling protocol.
  This is the project's ceiling, and the 2026-08-31 retirement made it
  concrete: every decision that day — which population to serve, which events
  to admit, whether the recovery was worth importing — was settled by counting
  rows, comparing sets and measuring bytes. Not one was settled by whether the
  answers got better. memstore is now switched off on structural evidence
  alone, which is enough to call it an operational replacement and not enough
  to call it an improvement.

## Integrations
- [!] Windsurf and Trae remain unindexable at layer 1: the Windsurf exporter
  emits 0 conversations from its 4 database artifacts, and the Trae exporter
  emits VS Code workspace metadata instead of dialogue. Both filed in
  `~/p/rocket-agents/TODO.md`; smallest unblock is fixing those exporters
  (needs authorization to change that repo).

## Durability

- [!] **The synthesis registry is on one disk and nothing replicates it.**
  Measured 2026-09-01: `~/.local/share/atrium/synthesis/records` holds 17,456
  records, 94 MB — several weekly Google AI Pro cycles on the agy lane plus the
  383-episode Max tranche that cost 4.7M input tokens. It is the one thing here
  that is *not* disposable: the index rebuilds from it, and it rebuilds from
  nothing but paid model calls. Evidence that it is unprotected: no sync script
  under `~/p/dotfiles/bin` names the path (`sync-all-safe` and
  `sync-conversations` move the archive only); `tmutil destinationinfo` reports
  **no Time Machine destination configured at all** on this machine; and
  `peer-b` — reachable, and the host carrying the archive snapshot — has no
  `~/.local/share/atrium/` directory whatsoever. `backup_synthesis_records`
  copies to a sibling directory on the same disk, which is protection against a
  bad re-key, not against losing the disk.
  This is the same class as the archive-on-one-disk defect closed 2026-08-31;
  the registry was simply missed, and the pinned design already says it should
  be "synced by the dotfiles transport, never the SQLite index".
  Blocked because the fix changes a recurring automation in another repo:
  filed in `~/p/dotfiles/TODO.md` with the smallest step (add the registry to
  the existing transport, one designated writer, other machines consume).

## Self-improvement

- [ ] Query log, gap detection, and brain proposals. The durable-state
  contradiction this waits on is no longer abstract — it is the Durability item
  above, and a query log would add a *second* unreplicated store next to it.
  Resolve the placement rule first (brain, or an explicitly backed-up sidecar
  that the transport actually carries), then build; layer 2 must stay
  disposable, and as designed today a rebuild would erase both.

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

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
  398 while the denominator nearly tripled, because the mempalace recovery and
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
  **2026-09-04: the drip's lane is now configuration, not code.** It moved to
  codex when the Gemini weekly quota was spent (nothing produced on 09-01,
  09-02, 09-03) and back to agy the same evening when Antigravity reset, and
  rewriting the loop twice in one day is what `lane.env` exists to stop:
  `LANE`, `LANE_ARGS`, `QUOTA_PROVIDER` and `WORKERS` in one file, with the
  codex alternative kept commented beside the live setting. `drip-quota.py`
  takes the provider as an argument and still treats `usageKnown: false` as no
  evidence of headroom; `drip-guard.sh` kills a pass whose `run.log` sits idle
  1,800 s; a wall the probe cannot see sleeps 1,800 s blind. The codex lane
  now raises `QuotaExhaustedError` on a usage-limit reply (`71ef603`) -- it
  had no wall detection at all, so a spent window would have grated 44,000
  conversations into `FAILED` lines the way the agy lane did in August.
  Measured on the codex lane's 55 minutes: 1,213 records, and the account's
  **weekly Codex quota went 70% to 72%, about 3% per hour** -- roughly nine
  hours of drip before the wall, on the same quota interactive Codex work
  spends. agy is the standing routing rule for exactly that reason, and its
  population also outranks `gpt-5.6-terra-low` in `active-recipe.json`.
  Switching lanes means killing the running loop by process group first: two
  overlapping passes read `done_episodes` at their own start and pay for the
  same episodes twice.
  **The lane economics, measured over two full passes on 2026-09-04/05.** A
  pass runs until the Gemini 5-hour window is spent, and each one costs about
  a sixth of the weekly window:

  | pass | workers | weekly cost | records | records per point |
  | --- | --- | --- | --- | --- |
  | A | 8 | 16.78 pts | 391 | 23.3 |
  | B | 3 | 16.70 pts | 544 | 32.6 |

  Two things follow. First, **more workers do not buy throughput on this lane
  and cost quota**: 3 workers produced 12.3 records/min against 8 workers'
  14.0, a 1.14x return on 2.7x the concurrency because agy rate-limits server
  side, and pass B got 39% more records for the same quota. Both passes had 9
  real call failures, so retries were not the difference; episode size varies
  between passes and confounds the comparison, but nothing here argues for
  raising workers. Sized at 3 in `lane.env` with the measurement written down.
  Second, and this is the number that decides the project: a **full Gemini
  weekly window is worth roughly 2,300-3,300 records**, so against ~150,000
  pending episodes the agy lane alone is on the order of a year. The weekly was
  at 50.7% after two passes; the ~3 windows left before the 2026-09-10 reset
  are worth about 1,600 more records.
  For comparison the codex lane produced ~1,213 records for about 2 points of
  its weekly window, which is 13-39x more records per unit of quota (the range
  is honest: CodexBar reports that window in whole percent, and other codex
  activity on the account contaminates the reading -- a `codex exec --yolo`
  from another session was measured burning it during the comparison). It is
  also the account's *interactive* Codex quota, which is why the lane is an
  operator decision and not an optimization to apply.
  Remaining: decide the lane against those numbers (agy alone, codex, or
  alternating agy while it has a window and codex while it sleeps), re-run
  `ingest-synthesis` + `embed` periodically (the hourly refresh does both), and
  spot-check quality with Codex as evaluator. **Design pinned in the 2026-08-27 two-agent
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

- [ ] **Status review 2026-09-04, after four days unattended.** Working: the hourly
  refresh has run 141 times, last done 16:08 (25-35 min per hour, all of it the whole-archive
  rewrite filed under Ingest / Store); recall fires in both Claude profiles
  (`~/.claude-favish/projects` is a symlink into `~/.claude/projects`, so Favish sessions are
  captured); the Mac mini's sessions reach the archive through the daily `sync-all-safe`
  leg (verified on mini-only sessions of 09-03 and 09-04). Fixed the same day: the Mac mini
  now runs Atrium with its own index and hourly refresh, MemPalace is gone from it, and its
  copy of the synthesis registry is the second disk the Durability item asked for (see
  `TODO_LOG.md` 2026-09-04). Still open:
  * The agy drip produced **nothing on 09-01, 09-02 and 09-03** -- `drip.log` shows three
    consecutive `sleeping 86400s` against the Gemini weekly wall -- and 405 episodes on 09-04
    before the next wall. Newest-first ordering (`cli.py:440`) means the recent days do get
    memory first, but ~150k episodes of backlog at ~400/day is not a plan. Same open decision as
    the Synthesis item: pay the codex lane on a schedule, or accept partial coverage.
  * Coverage 38 of 51 projects (75%). `staffbase-global-content` (495 conversations) and
    `smart-sales` (114) have zero memory; `atrium synthesize --project` can fill them the next
    time a lane has quota.
  * Disk: index 20 GB, archive 5.2 GB plus one 5.2 GB backup, the retired mini MemPalace copy
    28 GB at `~/.local/share/mempalace-macmini-retired-20260904/`, and the volume is at 94%.
  * A fused search measured 20 s and a `--words` search 12.5 s while the refresh was writing the
    index; re-measure idle before calling retrieval slow.

- [ ] **Session scratchpads are indexed as if they were projects.** Paths like
  `/private/tmp/claude-501/-Users-cristiandeluxe-p-agents-tools/<uuid>/scratchpad`
  carry a `workspace` and become their own workspaces in the index — found
  2026-09-01 while folding renames. They are per-session temporary directories,
  not projects: they inflate the workspace count that made coverage read 2.1%,
  they never match a live `project_workspace`, so nothing can ever recall them,
  and their content is scratch. Either map a scratchpad back to the project
  whose name it encodes (the path contains it) or drop the workspace entirely
  at ingest, but not silently keep them as phantom projects.

- [x] **Coverage was being measured against the wrong denominator.** "9.9% of
  conversations synthesized" is true and misleading. Measured 2026-09-01 by
  project instead: of 13,269 distinct workspaces only 284 have memory (2.1%),
  but 13,162 of those workspaces hold fewer than five conversations — they are
  directories someone opened once, not projects. Against projects with >=20
  conversations coverage is **53.8%**, and against those with >=100 it is
  **64%**. The memory already covers most of the work that matters, which is
  the number that should decide whether a whole-corpus backfill is worth
  buying. **Done 2026-09-01** (`9fc40b7`): `atrium status --coverage` reports
  it — 36 of 51 projects, 71% — and names the largest projects recall would
  answer nothing for. Behind a flag because the query scans all 1.1M records
  at ~44 s against 4 s for the rest of status, and the hourly refresh should
  not pay hourly for a number that moves by fractions of a percent.

- [~] **`atrium embed` sat at 0% CPU for twelve minutes printing nothing.** The
  network half is fixed and measured (`cached_model_file`, commit `23c3bb8`):
  the model load made three `hf_hub_download` calls that each revalidate the
  etag before falling back to the cache, costing 34.2 s against a packet-
  dropping endpoint versus 1.4 s normally, and now 1.4 s in both cases. The
  first diagnosis, a writer queued behind the refresh, was disproved by a
  controlled probe: a second writer raises `database is locked` after 30.9 s
  exactly as `busy_timeout` promises. Remaining, and why this is `[~]` rather
  than closed: 3 x 34 s is about 100 s, not twelve minutes, so the original
  observation is still not fully explained — either the retries stack worse
  than measured, or something else was also waiting. Worth one more look the
  next time a long command goes quiet; `embed` should also say what it is doing
  before the load, so the next occurrence is legible instead of mysterious.

> Filed 2026-08-31, from the mempalace retirement. Every defect that session
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
  production decisions ("better than mempalace" needs a number). Smallest
  unblock: the user labels a stratified question set over the corpus, or
  approves a labeling protocol.
  This is the project's ceiling, and the 2026-08-31 retirement made it
  concrete: every decision that day — which population to serve, which events
  to admit, whether the recovery was worth importing — was settled by counting
  rows, comparing sets and measuring bytes. Not one was settled by whether the
  answers got better. mempalace is now switched off on structural evidence
  alone, which is enough to call it an operational replacement and not enough
  to call it an improvement.

## Integrations
- [!] Windsurf and Trae remain unindexable at layer 1: the Windsurf exporter
  emits 0 conversations from its 4 database artifacts, and the Trae exporter
  emits VS Code workspace metadata instead of dialogue. Both filed in
  `~/p/rocket-agents/TODO.md`; smallest unblock is fixing those exporters
  (needs authorization to change that repo).

## Durability

- [ ] **The drip's own scripts live only in `~/.local/share/atrium/synthesis/`.**
  `drip-loop.sh`, `drip-quota.py`, `drip-guard.sh` and `lane.env` are the bulk
  synthesis producer's whole control surface -- which lane runs, which quota
  gates it, what kills a hung pass -- and they are in no repository, on the
  same single disk as the registry, replicated by nothing. Two of them were
  rewritten twice on 2026-09-04 and the only copies of the previous versions
  are `*.bak-*` files beside them. Same class as the registry item below, and
  cheaper to fix: they belong in `~/p/dotfiles/bin` (or this repo) with the
  live paths as symlinks, so a lane switch is a reviewable commit rather than
  an unrecorded edit on one machine. Not done during a running pass.


- [x] **The synthesis registry is replicated since 2026-09-04/05.** It held 17,456
  records on one disk when this was filed and nothing carried it: no sync script named the
  path, `tmutil destinationinfo` reported no Time Machine destination on this machine, and
  `macmini` had no `~/.local/share/atrium/` at all. It is the one thing here that is not
  disposable -- the index rebuilds from it, and it rebuilds from nothing but paid model calls.
  Closed by provisioning the mini with a full copy and adding `sync_synthesis_registry_to` to
  `~/p/dotfiles/bin/sync-all-safe` (`dc689ae` there), which pushes `records/` and
  `active-recipe.json` from the designated writer on every daily run and never deletes on the
  peer, exactly as the pinned design says. Verified 2026-09-05: 2,514 files, 9.7 MB
  incremental, both machines at 32,503 records with an identical manifest.
  Still open, and wider than this item: the MacBook has no Time Machine destination
  configured at all, and Backblaze now excludes the archive (see `~/p/TODO.md`).

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
- [ ] `mempalace` fork: the live palace embeds with the English-only default
  model over a ~77% Spanish corpus; switching to `embeddinggemma` (same 384
  dims, config-only) nearly doubles dense quality (R@10 40.8% -> 70.4%) at
  ~36 h CPU re-embed. Decision pending: worth doing while Atrium replaces it?
  Filed in `~/p/mempalace/TODO.md`.

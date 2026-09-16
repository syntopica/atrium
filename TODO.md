# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-09-08. History coverage: Partial —
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

- [ ] `baseline-py baseline check` reports two BPY001 findings that predate the
  state-directory work (verified 2026-09-15 by stashing it: still 2 new on a clean
  HEAD): `atrium/embed/model_repo.py` has no declaration and
  `atrium/ingest/decode_workspace_segment.py` carries `_descend` beside its unit.
  Smallest step: declare `model_repo.py` a data module in `baseline-py.toml` and
  move `_descend` to its own file, then re-run the gate.
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
  them. Each is filed separately below and in `~/p/agents/TODO.md`, but
  together they are the answer to "is the archive complete", and today the
  answer is no.

- [ ] **45 scratchpad conversations stay unattributed because their projects are gone.**
  The scratchpad decode (`7e0ca9b`) walks the real directory tree, so a project deleted from
  disk -- `p/atc-prototype`, `p/thewealthadvisor`, `p/agents-tools` -- cannot be decoded and its
  sessions lose their workspace instead of gaining one. The workspace-alias map cannot rescue
  them as things stand, because aliases are applied after the decode. Smallest step: consult the
  alias map on the encoded form as well, which is also what would let a renamed-and-deleted
  project keep its memory.

- [ ] **331 conversations lose their vectors on the next ingest.** `write_conversation`
  replaces rather than upserts and `vectors.record_id` cascades on delete, so every conversation
  the scratchpad decode remaps is re-embedded on the following `embed` run. One-off and cheap at
  this size, but it is the reason the next refresh will look slower than the ones around it --
  worth knowing before that is diagnosed as a regression.

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
  (the second Claude profile's projects directory is a symlink into the first, so its
  sessions are captured); the Mac mini's sessions reach the archive through the daily `sync-all-safe`
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
  * Disk: the 2026-09-04 measurements were index 20 GB, archive 5.2 GB plus one 5.2 GB backup,
    and 94% used. Corrected 2026-09-14: the retired MemPalace copy is on the MacBook,
    not the mini (`du -sk`: 27,416,464 KiB). The named path is absent on the mini;
    its residual repository, launchers and plugins were backed up and removed there.
    The mini still measures 96% used. During the retirement task, another operation moved
    the MacBook copy to `~/p/wiki/mem/mempalace/macmini-retired-20260904/`; its adjacent
    README retains it as raw material for a possible Atrium ingestion pass. The retirement
    task did not delete it or authorize ingestion. The local retirement backup also moved
    to `~/p/wiki/mem/mempalace/this-mac-retired-20260914/` and its hashes were reverified.
    Evidence and exact before/after disk measurements: `~/p/TODO_LOG.md`, 2026-09-14.
  * A fused search measured 20 s and a `--words` search 12.5 s while the refresh was writing the
    index; re-measure idle before calling retrieval slow.

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
  **The legibility half is done 2026-09-08 (`e52b6d9`)**: every step that can block now
  announces itself and flushes -- opening the index, counting pending records, loading the
  named model (from cache or network, probed without touching the network and across all
  three files the load needs), then the batch size. What stays open is only the diagnosis:
  the next time embed goes quiet the log will name the step, and that is the evidence this
  item has been missing.

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

- [x] **The drip runs under launchd and the local lane waits for an empty desk.** 2026-09-16:
  `com.cristian.atrium-drip` runs `drip-launch.sh` (guard, then the loop), restarting the
  pair after a crash but not after a clean finish. The `local` lane leads `LANES` but is
  gated on `IDLE_ONLY`: `HIDIdleTime` over `IDLE_START` (600 s) and AC power to start, and
  a watcher cuts the pass by process group under `IDLE_RESUME` (120 s). Proved with
  `IDLE_START=1 IDLE_RESUME=99999`: pass admitted, cut 20 s later, exit 143, lane rechosen,
  no orphan. dotfiles `21e0279`.

- [ ] **The drip's stall guard kills any other synthesize pass on the machine.**
  `drip-guard.sh` finds its target with `pgrep -f "atrium synthesize"`, which matches *any*
  pass, and judges it against the drip's own `run.log`. While the drip sleeps against a quota
  wall that log does not move -- it has not moved since 2026-09-05 -- so the idle time is
  always over the threshold and any manually launched pass is killed within 120 s of starting.
  Found 2026-09-08 when a `--producer max` pass died silently twice before the cause was
  visible; the run printed nothing and exited, which reads exactly like a broken lane.
  The guard also violates the rule it was written under: watch the pid you launched, not a
  name pattern. Smallest fix: have `drip-loop.sh` pass its pass pid to the guard and have the
  guard `kill -0` that pid, so the guard is scoped to the pass it armed for.

- [~] **The session producer is built and registered; its first hook-driven record is
  still to be observed.** 2026-09-16: `atrium session-stop` and `atrium record-session`
  (`7e646ed`, `368720a`), design `docs/designs/session-producer.md` (revision 2 after a
  17-finding Codex review). Verified by hand: the hook answered a real Stop payload for
  the building session in 0.43 s with a `block` decision, froze checkpoint
  `db873a466347eb3a`, and `record-session` wrote `355ed3ffdcd616e7544e850820a9e9eb`
  (population `session-claude-fable-5-1`, workspace `[HOME]/p/brain`). Registered in
  `~/.claude/settings.json` under `Stop` (dotfiles `claude-export` carries it per host).
  **Live at 12:0x the same day:** Claude Code fired the hook in an unrelated interactive
  session (portfolio repo), the model obeyed, record `42b23dcc6f5cb41cf1dd4378959adb57`
  (12 facts, 5 open ends, workspace `[HOME]/p/cristian-deluxe-developer-portfolio`).
  The terminal shows the whole reason as "Stop hook error: ..." so the reason was cut
  to three sentences and the contract moved to `record-session --help` (recipe-2).
  Remaining: the retry accounting has only unit tests; decide
  whether `claude -p` sessions should be excluded outright (they are `entrypoint: cli`);
  put `session-*` populations first in `active-recipe.json` once a few exist. 2026-09-16 pm:
  the hub documents the hook (syntopica `c207031`); the refusal carries a `systemMessage`
  and `suppressOutput` (`3433fbf`) but this Claude Code build still prints the whole
  reason as "Stop hook blocking error" (claude-code #50542), so the person-facing line
  waits on upstream; the byte limit now counts user and assistant records only, after a
  post-compaction instruction re-read (attachments, ~100 KiB) tripped it on a one-line
  status turn.

- [ ] **One episode in 28 is a bare "structured output delivered" acknowledgement and
  still costs a full synthesis call.** Measured over the 3,165 records the drip wrote on
  2026-09-16 between 04:30 and 11:45: 111 have no facts, and their titles are variations of
  "Structured output provided successfully" (18), "Structured output confirmation" (9),
  "Structured Output Delivery Confirmation" (7)... These are the tail of a Codex subagent
  session where the last turn is only the StructuredOutput tool call and its
  acknowledgement, cut into an episode of its own by the segmentation. On the cursor lane
  each such call still pays the ~24k-token fixed prompt overhead (58.2M input tokens for
  1,640 records that day, 35k per episode). Smallest step: in the segmentation, fold an
  episode whose only assistant content is a tool acknowledgement into the previous
  episode; failing that, have `synthesize` skip episodes under a content-size floor and
  record them as skipped rather than calling. Evidence: `records/*.json` with
  `output.facts == []` from that window; the agy lane records `usage` as zeros, so its
  cost for these is not measurable.

- [ ] **The agy lane's Claude models cost 15x what Gemini does per record.** Antigravity
  meters Gemini and Claude/GPT on separate 5-hour and weekly windows, so a Gemini wall
  leaves `claude-sonnet-4-6` runnable (`--producer agy --model ...`, population
  `agy-claude-sonnet-4-6`, `df710f6`). One measured pass, 2026-09-16 13:08-13:14, wrote
  30 records and took the Claude/GPT weekly window from 19% to 54.7% -- ~1.2 points per
  record, where a Gemini pass buys ~450 records before walling -- out of the same budget
  interactive Antigravity work spends. The lane is off `LANES` (dotfiles `7196e6f`) and
  each lane now gates on its own windows via `QUOTA_WINDOWS`. Open question: whether
  those 30 records are enough better than Gemini's to justify a bounded run; nothing
  compares them yet, which is the acceptance-set gap again.

- [ ] **Bulk synthesis moved off Codex onto the Cursor lane, 2026-09-16.** Operator
  directive: the Codex account's quota is for interactive work and must not be spent
  here; the lanes are Cursor and agy. `--producer cursor` was added (`4844757`):
  `cursor-agent -p --mode ask --output-format json`, prompt on stdin, last balanced JSON
  object dug out of the envelope, population `cursor-<model>`. Bench in
  `docs/studies/cursor-lane-bench.md`: `gpt-5.3-codex-low` at 0 fabrications and 15-23 s
  per episode; `cursor-gpt-5.3-codex-low` appended last in `active-recipe.json`;
  `lane.env` in dotfiles switched to it. Measured in aggregate, ~0.005% of the monthly
  window per episode, so ~16,000 episodes before the 2026-10-10 reset. agy is blind, not
  merely walled: CodexBar reports no Antigravity limits at all (`Limits: not available`),
  so `drip-quota.py` answers 1800 for it forever and the loop would never run that lane.
  Same day, second directive: "use agy until it breaks, forget the quota". The drip
  (dotfiles `1d8d5ca`) now runs lanes in order, `agy cursor`: agy blind (no probe, stops at
  its in-pass `Individual quota reached` wall), then a 3 h cooldown file `walled-agy` while
  cursor takes the passes, then agy again. The first cursor pass lost 7 of 8 failed
  conversations to the transcript-first prompt order (the model performed the security
  review the transcript asked for); fixed in `0b449d1`, 1 failure in the next 35.
  First live fall-over 2026-09-16 05:16: agy walled after 43 min and ~800 records (its
  5-hour window; ~390 on 2026-09-04), `walled-agy` written, cursor pass started one second
  later. Backlog counted the same day: 111,590 episodes, ~76,500 pending.
  Cursor's third-party window (CodexBar `tertiary`, 100%) does gate gpt/gemini/claude
  there: `gpt-5.3-codex-low` walled at 05:18 after 2.5 min; the lane runs the Cursor-native
  `composer-2.5` since 05:21 (1 soft fabrication on 3 episodes, 21-28 s, ~5 episodes/min at
  3 workers). `cursor-agent` leaves an `index.js worker-server` orphan per call: 38 of them
  held 7.4 GB after an hour; fixed by running the CLI in its own session and killing the
  group after each call (`run_cursor_in_own_session`).
  agy's retry at 08:59 hit the wall on its first call ("Resets in 22m43s"): the fixed
  3 h cooldown outlasted the reset, so the loop now parses "Resets in" into the cooldown
  (dotfiles `a1061dc`). Stopping that loop showed `timeout` runs the pass in its own
  process group: the agy pass outlived the loop by 14 min beside the new cursor pass
  (two producers at once, the thing the lock exists to prevent), and the killed pass
  left its `cursor-agent` sessions with parent pid 1 because SIGTERM skips `finally`.
  The loop's trap now kills the pass group and reaps those orphans after every pass
  (`aa39731`, `1f803e9`). Second agy window of the day: 10:14-11:01, ~450 records, then
  "Resets in 4h13m47s"; this time the three in-flight calls sat ~10 min (the
  `--print-timeout`) before answering the wall, so the pass outlived the box and the
  loop's time-box branch skipped the wall check: agy was picked again at 11:14 against
  its wall. Wall check now precedes the box branch (`95c547f`).
  Remaining: read the first day's `run.log` and CodexBar to size `WORKERS` and confirm the
  per-episode cost; make a SIGTERM to `atrium synthesize` end its cursor-agent sessions
  itself (a signal handler that kills the in-flight groups) so the reaping is not the
  drip's job; find why CodexBar lost the Antigravity windows (it read them on
  2026-09-04) so agy can be gated again instead of walled.

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
  `~/p/agents/TODO.md`; smallest unblock is fixing those exporters
  (needs authorization to change that repo).

## Durability

## Self-improvement

- [ ] Query log, gap detection, and brain proposals. The durable-state
  contradiction this waits on is no longer abstract — it is the Durability item
  above, and a query log would add a *second* unreplicated store next to it.
  Resolve the placement rule first (brain, or an explicitly backed-up sidecar
  that the transport actually carries), then build; layer 2 must stay
  disposable, and as designed today a rebuild would erase both.

## Cross-project

- [ ] **The two machines' archives are not identical after a two-way sync.** Found
  2026-09-05 by running `atrium doctor` on the newly provisioned Mac mini: it warns
  `9 conversations no longer archived` -- nine conversations that have paid synthesis
  records but are absent from the mini's archive -- while the same check on the MacBook
  reports zero. The nine are old (2026-07-15 to 2026-08-09), so this is not the
  registry-ahead-of-archive lag it first looked like. Counts diverge in both directions:
  43,995 indexable conversations on the mini against 43,991 on the MacBook, after
  `sync-conversations ... sync` ran both legs on 09-04. The merge is supposed to be a union,
  so a set difference either way is either an import that silently dropped records or a
  leg that did not complete. Small (9 of 32,503 records) and not urgent, but it is exactly
  the silent-loss class the archive design exists to prevent, and it will be masked once the
  v2 journal lands. Smallest step: dump both archives' conversation id sets and diff them,
  then look for those ids in the import logs. Cross-project: rocket-agents, dotfiles.


- [ ] `rocket-agents`: canonical event IDs are conversation-local in practice —
  `conversationEventFromRecord.ts:20` derives them from `event_index + text`
  with no conversation identity, and real cross-conversation collisions were
  measured (OpenCode, Cursor). Atrium works around it with
  `sha256(conversation_id, event_id)`; the canonical contract should carry the
  identity itself. Also: the Windsurf exporter emits 0 conversations from 4
  database artifacts. Filed in `~/p/agents/TODO.md`.
- [ ] `mempalace` fork: the live palace embeds with the English-only default
  model over a ~77% Spanish corpus; switching to `embeddinggemma` (same 384
  dims, config-only) nearly doubles dense quality (R@10 40.8% -> 70.4%) at
  ~36 h CPU re-embed. Decision pending: worth doing while Atrium replaces it?
  Filed in `~/p/mempalace/TODO.md`.

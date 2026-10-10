# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-09-08. History coverage: Partial —
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

- [ ] A notes-only FTS table is the remaining lexical idea, and it is now an
      optimisation rather than a fix. A second-opinion run built one over the 4,865
      curated notes (513ms, 11.34 MB) and measured its unpruned broad query at a
      0.345ms median against 1,078ms for the shared table, with candidates for 12/12
      probe questions instead of 6/12. Since then the rank-ordered read took the
      shared table's broad pass to 0.15-0.85s with no budget exhaustion, so what is
      left to win is the frequency pruning: a notes-only table can afford the
      unpruned OR. Cost is maintenance -- a second index to build, refresh and keep
      consistent with `records` -- and the bm25 statistics change, so the ranking
      would have to be compared against the current one on the same questions before
      this is worth it. Measurements in the review directory's `notes-summary.json`.
- [!] Dense-over-raw stays an explicit reserve lane: even with an oracle
  embedder the zero-lexical-overlap class recovers only 3 of 25 from synthesis
  alone. "No ANN" is not approved until the reserve lane is measured at full
  corpus scale. Blocked by the same condition as the Measurement item below
  (2026-09-01): the only question set is machine-extracted, and this item
  exists precisely to justify a production decision ("no ANN"), which that set
  cannot do. Smallest unblock: the hand-labeled set, then the measurement is
  hours of embed CPU plus the existing eval harness.

## Ingest / Store

- [~] **Process the retired MemPalace store into Atrium, then delete it** (owner,
      2026-09-16: "tenemos que procesarlo y luego borrarlo"; approved again 2026-10-10).
      The copy is `~/p/wiki/mem/mempalace/macmini-retired-20260904` (26 GB, `uchg`, the only
      copy, ignored by the wiki repo); `this-mac-retired-20260914` beside it is 116 MB.
      Sampled read-only 2026-10-10 (Codex review): `palace/chroma.sqlite3` holds 464,413
      embeddings in one collection, `mempalace_drawers`: 462,311 conversation ingests, 880
      registry records, 2,058 diary entries (`CHECKPOINT` tails); `knowledge_graph.sqlite3`
      2,897 entities, 1,912 triples, byte-identical in all three palaces. The older Chroma
      stores hold 773,187 (`palace.pre-merge-20260811`) and 1,136,075
      (`palace.pre-rebuild-20260821-002808`) embeddings, so they may carry records the
      current palace lost. Plan: conversation chunks and diaries are re-derivable from the
      archive; export only registry, diary-free synthesis (`runbooks`, `gotchas`,
      `decisions`) and the triples to a redacted JSONL with source ids and content hashes,
      drop what matches the archive, existing synthesis or Brain notes, publish the rest as
      sourced Brain notes, then `ingest-notes`. Vectors and triples never go into the
      disposable index directly. Deletion only after a hash manifest of all three palaces,
      every snapshot-only record reviewed, and the owner confirming the exact target.

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
      codex gap is closed (streaming export since 2026-08-31; every refresh reports
      `skipped: 0` over 31,119 codex artifacts); the Windsurf and Trae exporters emit zero conversations; ChatGPT
      and Grok leave no local transcript, so nothing has ever been captured from
      them. Each is filed separately below and in `~/p/agents/TODO.md`, but
      together they are the answer to "is the archive complete", and today the
      answer is no.

## Synthesis

- [ ] Episode-level synthesis is the heart of the system, not phase 2: dense
      vectors cover only synthesized content, so synthesis quality _is_ semantic
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
  - The on-disk `active-recipe.json` listed only
    `["codex-cli-default","claude-sonnet-5"]`, so the whole
    `gemini-3.7-flash-medium` population -- 3,686 episodes across 580
    conversations, a quarter of everything synthesized -- was produced and
    then dropped at ingest. Adding it took served coverage from 2,029 to
    **2,609 conversations** and 11,835 to **14,653 records**, with no calls.
  - `drip-quota.py` read only the `Gemini 5-hour` window. That window reports
    `usedPercent 0` with `usageKnown: false` while `Gemini weekly` sits at
    100%, so the probe answered "go now", every pass aborted on its first
    call, and the loop ground for ~18 h logging `failed=10790` with zero
    output. It now reads every Gemini window, treats `usageKnown: false` as
    no evidence of headroom rather than as headroom, and sleeps to the
    furthest reset (cap raised 4 h -> 24 h, since the weekly wall is ~14 h out).
  - The loop had died outright (no process since 08:12) and nothing restarted
    it. It now takes a `mkdir` lock with a stale-pid check -- macOS has no
    `flock(1)` -- so a second start exits instead of doubling the quota burn
    the way the 2026-08-28 orphan did.
    Coverage after the fixes was 2,609 of 11,028 archived conversations (23.7%).
    **Re-measured 2026-09-01: 3,007 of 30,318 (9.9%)** — the numerator grew by
    398 while the denominator nearly tripled, because the memstore recovery and
    the second machine capture added conversations far faster than a quota-walled drip
    can synthesize them. Coverage is now falling, not rising, and the drip has
    been sleeping against the weekly Gemini wall since 2026-08-31 23:22. One day
    of agy work on 2026-08-28 (13,966 records) spent an entire Google AI Pro
    _weekly_ quota, so the remaining corpus is many weekly cycles on that lane
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
    there is no cheap prioritization escape — the recent work _is_ the bulk.
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
  | ---- | ------- | ----------- | ------- | ----------------- |
  | A    | 8       | 16.78 pts   | 391     | 23.3              |
  | B    | 3       | 16.70 pts   | 544     | 32.6              |

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
  also the account's _interactive_ Codex quota, which is why the lane is an
  operator decision and not an optimization to apply.
  Remaining: decide the lane against those numbers (agy alone, codex, or
  alternating agy while it has a window and codex while it sleeps), re-run
  `ingest-synthesis` + `embed` periodically (the hourly refresh does both), and
  spot-check quality with Codex as evaluator. **Design pinned in the 2026-08-27 two-agent
  consult, one amendment by operator directive:**
  - Producer, second amendment (operator, 2026-08-28): the Codex CLI's own
    quota (`--producer codex`, default) after the Max lane measured 4.7M
    input tokens for 383 episodes; the Max lane stays as `--producer max`.
    Populations never mix: the model id is in the job key and the
    active-recipe manifest picks exactly one record per episode at ingest.
    The one-producer-population and codex-as-evaluator clauses of the
    original consult are amended by these operator directives.
  - Segmentation: `episode-texttiling-v1` — turn blocks per human message;
    hard cuts at reset markers; TF-IDF TextTiling over human turns only
    (bilingual ES/EN stopwords), three-turn windows, valley depth > session
    median + 1 MAD, >=2 human turns between cuts; 32k-token ceiling with one
    pinned tokenizer; oversized coherent episodes map-reduce mechanically and
    the map chunks are never retrieval episodes. Deterministic, no LLM and no
    embeddings in the cutter.
  - Storage: immutable content-addressed registry at
    `~/.local/share/atrium/synthesis/` with an atomic active-recipe manifest;
    one designated synthesis writer, other machines consume; synced by the
    dotfiles transport, never the SQLite index.
  - Every record carries the full recipe (archive hashes, episode id +
    ordered event hashes, segmentation fingerprint, provider + exact model
    snapshot, prompt sha256, output schema version, inference params,
    generator version, parent map ids, output sha256). Job key = hash of all
    inputs minus output; same job key with different output hashes is a hard
    divergence error, never resolved by timestamps.
    Only user-approved notes are proposed to brain (a tray, not a dump).

## Promotion pipeline

- [x] Stage one, `atrium curate-screen`: 47,753 records and 306,212 facts into
      288,844 distinct candidates, 12,693 quarantined by named reason.
      **Exact deduplication removes 1.59%, not the 5% first reported** -- the
      5% divided by all facts instead of the eligible ones, so it counted the
      quarantine as deduplication. 293,519 eligible occurrences become 288,844
      candidates. The corrected figure says the same thing more sharply: the
      repetition in this corpus is paraphrase, and the semantic merge is the
      expensive stage.
- [x] `normalized_claim` collapsed a sign, a comparison and a version
      separator: "retention limit -3 days" matched "retention limit 3 days",
      "x >= 3" matched "x < 3", "version 1.2" matched "version 1-2". Found by
      a second opinion, reproduced here, fixed in `protected_symbols`
      (`c18515c`), ledger rebuilt. Keeping digits was never enough; the symbols
      around them carry the meaning.
- [x] Stage two, `atrium curate-extract`: 498 claims structured against
      qwen3.6:35b at 1,484/hour under drip contention and 2,392/hour without,
      0 failures, off every quota. The whole ledger would take about 190 hours
      on this lane alone, so a full pass is a scheduling decision, not a run.
- [x] Graded 60 claims of the working set by hand, 2026-09-17. Scope 83%
      correct (10 wrong, every error in one direction: a project claim called
      `general`, or the operator's own code called a `tool`), durability 93%
      correct, and **25% of claims lost an assertion or came back with an empty
      value** because the sentence carried more than one. 12% were session
      debris stage one had passed, now quarantined (`0afffad`). About 37% of
      the sample is durable and specific enough to be worth publishing.
- [-] Deriving `scope` from code tokens in the sentence: measured and rejected.
  It flips only 7 of 67 `general` claims and misfires (an IBAN and a Slack
  timestamp read as code, while `lefthook`, `prettier` and `WP-CLI` are
  genuine tools that quote paths). `project`, resolved from the index, is
  the strong routing signal; `scope` is a weak one and stage three should
  treat it as such.
- [ ] The subject/predicate/value triple is the suspect part of the claim
      schema: it degrades a quarter of the sample and adds nothing the sentence
      does not already carry. Consider replacing it with an `entities` list of
      quoted identifiers, which is what a merge actually needs, and keeping the
      sentence as the claim. Decide after the stage-three design lands, because
      the merge algorithm is what says which fields it needs.
- [x] The first holdout was not untouched: 29 of its 102 rows were already in
      `claims.jsonl`, because the sampler fix moved members between the two
      sets and the resume had already extracted the old draw. Both files are
      kept under `curation/superseded/` and the evaluation set was redrawn from
      the rebuilt ledger. A holdout is only untouched if nothing has ever
      extracted it -- record its hash when it is drawn.
- [ ] Spend the new 100-claim holdout once, on stage three's acceptance, not on
      stage two. Two failure shapes are already visible and neither is
      fixed by prompt-fiddling: a sentence carrying two assertions loses one
      (the Apache 503 claim kept "contains maintenance downtime" and dropped
      "now reads the title first"), and a claim whose sentence names no file or
      repository is classified `general` even when it is plainly about one
      project (`/findings expects to be an array`, in project-after). 64 of 498 came
      back `general`; that is the number to check by hand.
- [ ] 276 of 498 claims are `situational` -- true of one run, one session, one
      transient state. They are the population stage three must not publish,
      and the ratio says over half the extracted corpus is not brain material
      at all. Confirm the label is right before trusting it as a filter.
- [ ] Stage three: semantic merge and page proposal. Inputs are the claims
      ledger plus the entity lifecycle question (a claim about a renamed or
      replaced tool is worse than no claim). It writes proposals only:
      `AGENTS.md:24` forbids writing the curated layer, and the pilot that did
      so had to be reverted with `git checkout`.
- [ ] The claim ledger stores `project` as resolved at extraction time. It is
      derived from the index and cheap to recompute, so if the resolution rule
      changes again, rewrite the field rather than re-calling the model -- the
      first two rules changed 42 of 527 rows between them.

## Observability

- [~] **Refresh runs went from 12-15 min to 1-2.5 h on 2026-10-09.** Each stage now
  logs its start (dotfiles db6b097), so the next slow run names its step; the 22:45
  run was back to 13 min. Suspect: the import waits up to 5400 s on the archive
  lock that `sync-conversations` also takes. `refresh.log`:
  13:27-15:42, 16:54-19:19 and 20:19-21:28 (local), against 11-23 min for every run on
  2026-10-08; record counts grew by only a few hundred. No run since the stage logging
  landed has been slow (22:45 took 13 min), so the evidence is still to come. Smallest
  next step: when a run passes 30 min, read the `stage` lines in `refresh.log` and name
  the step; the archive is 6.7 GB and rewritten whole on every import, which is the
  first suspect (see Ingest / Store).

- [ ] **`synthesis recent` costs 2-6 s** because `daily` opens every record
      of its window (15,696 files for 14 days). If a reader ever needs it
      polled, keep per-day totals for closed days in a derived file.

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

> Filed 2026-08-31, from the memstore retirement. Every defect that session
> found had been running silently for days, and none of them were subtle --
> they were invisible because nothing reported the right number.

- [x] **The drip runs under launchd and the local lane waits for an empty desk.** 2026-09-16:
      `com.cristian.atrium-drip` runs `drip-launch.sh` (guard, then the loop), restarting the
      pair after a crash but not after a clean finish. The `local` lane leads `LANES` but is
      gated on `IDLE_ONLY`: `HIDIdleTime` over `IDLE_START` (600 s) and AC power to start, and
      a watcher cuts the pass by process group under `IDLE_RESUME` (120 s). Proved with
      `IDLE_START=1 IDLE_RESUME=99999`: pass admitted, cut 20 s later, exit 143, lane rechosen,
      no orphan. dotfiles `21e0279`.

- [ ] **One episode in 28 is a bare "structured output delivered" acknowledgement and
      still costs a full synthesis call.** Measured over the 3,165 records the drip wrote on
      2026-09-16 between 04:30 and 11:45: 111 have no facts, and their titles are variations of
      "Structured output provided successfully" (18), "Structured output confirmation" (9),
      "Structured Output Delivery Confirmation" (7)... These are the tail of a Codex subagent
      session where the last turn is only the StructuredOutput tool call and its
      acknowledgement, cut into an episode of its own by the segmentation. On the cursor lane
      each such call still pays the ~24k-token fixed prompt overhead (58.2M input tokens for
      1,640 records that day, 35k per episode). Update 2026-10-09: the cost
      half is moot -- bulk now runs on the worker's agy and local lanes, not the cursor
      lane -- so what is left is retrieval noise: such titles show up in recall. Folding
      them in the segmentation changes the event ids of the episode they join, so it
      re-keys and re-pays that episode; a content-size floor that records them as
      skipped does not. Decide which before building. Evidence: `records/*.json` with
      `output.facts == []` from that window; the agy lane records `usage` as zeros, so its
      cost for these is not measurable.

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
  `~/p/agents/TODO.md`; smallest unblock is fixing those exporters
  (needs authorization to change that repo).

## Quality gate

## Self-improvement

- [ ] Query log, gap detection, and brain proposals. The durable-state
      contradiction this waits on is no longer abstract — it is the Durability item
      above, and a query log would add a _second_ unreplicated store next to it.
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
      database artifacts. Filed in `~/p/agents/TODO.md`.

## Routed from `~/p/TODO.md` (2026-10-03)

Moved verbatim from `~/p/TODO.md` on 2026-10-03; the routing table in
`~/p/TODO_LOG.md` (entry of that date) records each move.

- [x] **`atrium status --json` is rejected (`unrecognized arguments`).** Fixed: `status --json`
  prints the redacted refresh document (same as `--publish`, writes nothing); `doctor`,
  `prepare` and `context` already had `--json`. No guidance elsewhere referenced it.

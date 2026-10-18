# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-10-11. History coverage: Partial —
> Atrium was designed and built inside the `~/p/memstore` project history
> (session `a88ac62e`, 2026-08-25 to 2026-08-27, plus one Codex review
> rollout); that history is fully parsed here. The older memstore sessions
> cover the fork itself and are consolidated in `~/p/memstore/TODO.md`, not
> reparsed here.
>
> States: `[ ]` pending · `[~]` partial or unverified · `[!]` blocked · `[x]`
> verified complete · `[-]` obsolete or superseded. Closed work moves to
> `TODO_LOG.md`.

## Ingest / Store

- [~] **Segment archive v2 stage 3, workstream 2 (scribe plan
  `docs/plans/2026-10-11-segment-archive-v2-stage-3.md`, contracts at scribe `31d70f8`).**
  No live cutover before the parity and recoverability checks pass. State on 2026-10-11:
  - Done: the slice fixture is vendored (`tests/fixtures/scribe_pending_slice_v2.jsonl`)
    and `ingest --partial` writes its conversation and leaves every other row and vector
    untouched (`tests/test_scribe_segment_contract.py`). `--partial` never calls
    `mark_revision_backfill`: that stamp tells the synthesis ingest that revisions cover
    every archived conversation, and a slice covers a subset.
  - Done: a full ingest after a generation change removes an erased conversation's rows,
    revision and vectors.
  - Done: `atrium erase --plan <applied plan> [--apply]` (fixture
    `tests/fixtures/scribe_erasure_plan_v2.json`). Under `refresh.lock` and
    `synthesis/synthesis.lock` it journals every identifier, then deletes the registry
    records (backups included), the raw and `synthesis/` rows and revisions (vectors by
    cascade), every partial, the curation rows, files and proposal runs that name them
    (matrix kept aligned with its id list), and the saved dense matrix. It refuses an
    index other than the instance's, and an archive whose manifest does not name the
    plan's `toGenerationId` as `generationId` or in `generationLineage`. Codex reviewed
    it in 8 rounds.
  - Done: scribe `293a740` stamps `generationId` and `generationLineage` (ancestors,
    newest first) on `export-materialized` and `export-pending`. Its
    `materialized-after-erasure.jsonl` is vendored and the apply tests run against it.
    Not yet run against the live archive.
  - Done 2026-10-16: a full ingest records the manifest's `generationId` in the index
    (table `archive_generation`, cleared by an archive that names none; `--partial` never
    writes it), and `doctor --segment-inventory <file>` reads `scribe segments-inventory`
    JSON and warns `archive_generation_stale` or `archive_deliveries_pending`
    (`tests/test_archive_generation_and_parity.py`). Remaining at cutover: the refresh
    (dotfiles) runs `scribe segments-inventory` and passes its output to `doctor`; Atrium
    does not run scribe itself. The `--state` location is decided (scribe TODO, owner
    2026-10-11: `~/.local/state/rocket-agents/conversations/`); what blocks the refresh
    wiring is that nothing live writes segments yet. Scribe's side of stage 3 landed
    2026-10-18: `scribe erase` (`9165eed`), `relativePath` as an array (`1136f5b`, fixtures
    re-vendored here `f1bdcdd`), redaction replacement (`829abe0`), `segments-receive` and
    `segments-seed-generation` (`3d4f2fb`), the freeze sentinel with exit 75 (`a3b8a34`) and
    `scribe recovery-drill` (`7a33cdb`). The dotfiles side landed the same day (`58d7cfc`
    freeze gates and `conversation-writers`, `a36fe4a`, `cd71ade` segment modes of
    `sync-conversations` and the refresh, off until a host's `segment-mode` file exists);
    here `a8a5877` makes a generation's full ingest sweep a provider it no longer holds.
    Rehearsal on a copy of the live archive (scribe plan, `d129b51`): v1 to v2 record
    parity exact with scribe `d839d84`; the drill passed on a one-in-five subset. Left
    before the first real seeding pass: the full-size drill (running on an external disk;
    the internal one ran out at 88 GB).
  - Done 2026-10-16: `atrium --index <live> parity <test>` compares, read-only on both,
    records by id and text digest per provider (raw, notes, synthesis), the ranked probe
    of both FTS lanes on each side, and vector identities; exits 1 on any record
    difference. Live against itself: `equal`, 53 s, 494 MB peak. Done 2026-10-18 on the
    rehearsal copy: an index from the v1 archive against one from scribe `d839d84`'s
    `export-materialized` of its migration, no vectors: `equal`, 386,240 records in
    both FTS lanes, 0 changed or missing in every provider (claude-code 287,556, codex
    29,572, cursor 66,558, opencode 2,454, pi 63, openclaw 37); ingest 5 min each,
    parity 10 s. Repeat on the first live export at cutover.


- [ ] **The trigram lane is ~70% of the index and serves no traffic.** Measured
      2026-10-10: index 22.4 GB (5,473,158 pages of 4 KiB, freelist 566, so no bloat);
      `substrings_data` 3,800,043 blocks against `words_data` 387,204, roughly 15 GB
      against 1.5 GB at FTS5's ~4 KB blocks. Every insert pays both lanes through
      `records_ai`. Usage since 2026-09-01 across every Claude Code transcript: 0 calls
      with lane `substring` (152 `atrium_context`, 35 `atrium_search`, 2 of them dense,
      no CLI `--lane substring`). `dbstat` on 2026-10-11 (read-only, 416 s, 20,875 MiB
      over all objects): `substrings_data` 15,092 MiB (72%), `records` 3,361,
      `words_data` 1,580, `vectors` 169, every index under 160. The first day of lane
      telemetry logged 2 `substring` calls out of 96; the same day's trace of the
      `bench-`/`judge-` workspaces used `--substring`, a real fragment lookup that a
      `words` prefilter plus `instr` would also have answered. Smallest next step: re-read
      `atrium status --lanes` on 2026-11-11, after a 30-day window.
      Then obtain an owner decision between dropping the
      raw-corpus trigram table (fragment search answered by `instr` over a `words`
      prefilter, or trigram over notes and synthesis only) and keeping it. AGENTS.md's
      "word-level separate from substring" decision is about ranking, not about trigram
      over 1.9M raw records, but it must be re-read before changing the schema.
      2026-10-14: the admission cut took the index from 1,923,985 to 483,624 records,
      yet the file stays 23,331 MiB (5,972,727 pages, freelist only 213,437): FTS5
      keeps deleted rows in its segments until they are merged. Reclaiming the space
      needs an FTS `optimize` on both lanes and then `VACUUM`, and Atrium has no
      supported command for either; direct mutation is off limits. With 100 GiB free
      it is not urgent. Smallest step: an `atrium compact` command run under
      `refresh.lock`, sized after the trigram decision, since dropping that lane
      reclaims most of the same space.
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
  Update 2026-10-10: the schema 2 change has landed (the index reports "schema 2,
  pipeline 2"), so that collision is gone. The writer is rocket-agents, and the work is
  filed in agents at the time, now in `~/p/scribe/TODO.md`; this entry tracks only Atrium's side, the
  per-writer cursor for incremental ingest, which waits on that format.
  Correction 2026-10-11: "implementation is not started" above is stale. The segment
  archive's stage 2 landed in agents `8cc2849` (content-addressed segments, incremental
  capture; measured on 25,000 synthetic artifacts a warm no-op takes 1.91 s against the v1
  baseline of 226.91 s). Stage 3 remains: transport, erasure, the pending slice handed to
  `atrium ingest --partial`, and cutover. It moves with the capture code to
  `syntopica/scribe` (owner decision 2026-10-11).
- [ ] **Whole conversations that have never entered the archive at all.** The
      codex gap is closed (streaming export since 2026-08-31; every refresh reports
      `skipped: 0` over 31,119 codex artifacts); the Windsurf and Trae exporters emit zero conversations; ChatGPT
      and Grok leave no local transcript, so nothing has ever been captured from
      them. Windsurf and Trae are filed under Integrations below, but
      together they are the answer to "is the archive complete", and today the
      answer is no.

## Synthesis

- [ ] **Synthesis coverage and quality.** Built 2026-08-28 (`6263938`); the lane question is
      settled by the owner routing rule of 2026-09-30 (bulk on the worker's agy and local
      lanes, cursor cancelled, `drip-loop.sh` retired). The build history, the lane
      economics and the pinned design moved verbatim to `TODO_LOG.md` (2026-10-10).
      Coverage on 2026-10-10: 32,152 of 53,340 indexed conversations have synthesis
      (60.3%, from 9.9% on 2026-09-01); 69 of 74 projects with >=20 conversations have
      memory. Quality spot-check the same day, 10 random single-chunk
      `ollama-qwen3.6-35b` records read against their transcripts: 2 were harness echoes
      (now skipped), 5 faithful, and 3 carried a false claim -- "no security
      vulnerabilities found" for a review whose StructuredOutput payload is not in the
      transcript, gitleaks' "no leaks found" restated as "no memory leaks", and an Edit
      mismatch blamed on whitespace when the comment had been renumbered. Three of eight
      substantive episodes is a high error rate for the population now writing most new
      records. **Decided 2026-10-10 (owner):** no Codex for bulk; the order is agy,
      OpenRouter, local, Codex last or only to verify (`~/p/wiki/CLAUDE.md`, Model
      routing). The worker ladder for `atrium.synthesis` already follows it. The
      shadow judge agrees with the spot-check (30 days, `worker quality --days 30
      --json`): OpenRouter `qwen/qwen3.8-27b:free` 4.73 mean over 22 judged, agy
      `gemini-3.8-flash-medium` 4.05/19, dots 3.74/43, nemotron 3.64/67, local
      `qwen3.6:35b` 3.09/44. Local took most volume because agy rests and the
      OpenRouter route stopped at a fixed `daily_cap` of 350 while the key spent only
      402-876 of its 1,000 a day (2026-10-06..10). Fixed the same day: worker
      `4917c02` adds `daily_key_cap`, and the queue now uses OpenRouter until the whole
      key reaches 850, leaving 150 for the other queues (wiki `968b99623`). Remaining
      levers within the allowed lanes: a longer `local_after_s` for this backlog queue (higher quality,
      lower throughput), a better local model, or a faithfulness pass by an allowed
      lane before ingest. `qwen3.8:27b` locally was tried 2026-10-10 and is not it
      yet: Ollama 0.40 serves it only on the MLX runner, which answers any `format`
      with `501 structured output is unavailable`, and the worker always sends the
      schema. Speed is no obstacle on the M4 Max (18-32 tok/s generation against
      23-27 for the 35B MoE, 9-14 s per episode, 18 GB against 22), but with the JSON
      asked in the prompt it repeated the failures: a review verdict invented on one
      of the three episodes qwen3.6 got wrong, a failed Edit reported as applied on
      another. The OpenRouter score for the same model (4.73) does not carry over. Owner choice between throughput and quality; nothing
      changed yet. Same three episodes, 2026-10-10, newer local candidates: Ollama's
      default `gemma4:26b` (nvfp4) is MLX and 501s too; its GGUF
      `gemma4:26b-a4b-it-q4_K_M` runs (8-30 s) but erred on 2 of 3, inventing a
      repository name and the review verdict, so it was removed. `gpt-oss:20b`
      (12 GB, 6-10 s) erred on 1 of 3, the same invented "no vulnerabilities"
      verdict; qwen3.6:35b erred on 2. Three episodes are not a verdict. Switching
      also needs a worker change: `ollama_request_body` and `probe_quiet` send
      `think: false`, on which `gpt-oss:20b` with a `format` hung for over 15 min;
      it answered with `think: "low"`. Held-out comparison done 2026-10-10
      (`~/p/wiki/atrium/evaluations/lane-faithfulness-2026-10-10/`, local,
      git-ignored). It used 24 episodes, 8 each served by OpenRouter nemotron,
      OpenRouter qwen3.8-27b and local qwen3.6. Each was re-synthesized by local
      qwen3.6, agy `gemini-3.8-flash-medium` and `gpt-oss:20b` (llama.cpp on
      nova). GPT-6 judged all 1,021 title/summary/fact/open-end claims blind.
      Unsupported: OpenRouter qwen3.8-27b 6.1%, nemotron 9.8%, local qwen3.6
      21-23%, agy flash 23.1%, gpt-oss 23.9%. Matched episodes give the same
      order: on nemotron's 8 episodes, nemotron 9.8% against 24-35% for the
      rest; on qwen3.8's 8, qwen3.8 6.1% against 10-26%. A Codex review
      (same day) confirmed the numbers but limited the conclusions. The
      OpenRouter outputs are the served records, picked with at least two
      facts, while the other lanes were generated fresh. Served and fresh
      qwen3.6 on the same 8 episodes score alike (23.0% against 22.9%), but
      that does not remove the selection effect. The agy lane used atrium's
      prompt, not the worker's runner. gpt-oss ran on llama.cpp on nova's CPU,
      not on Ollama, so its 44 s against qwen3.6's 20 s describes these hosts.
      Provisional reading: gpt-oss:20b shows no faithfulness gain over
      qwen3.6, and OpenRouter looks like the quality lever. Its key already
      reaches the 850 cap most days, so a longer `local_after_s` only delays
      the backlog. **Owner approved the confirmation run 2026-10-11**; `gen_or.py` in the
      same evaluation directory is armed to start at 02:05 CEST on 2026-10-12 after the
      key's daily reset (`run_or.sh`, watchdog `watch_or.sh`, log `run_or.log`), stopping
      if the key's free headroom falls to 100. **Ran 2026-10-12 02:05-02:14:** nemotron
      24 of 24 generated (`gen_or-nemotron.json`); `qwen/qwen3.8-27b:free` 0 of 24, every
      request `HTTP 404`, so that model is gone from OpenRouter and the 6.1% lane cannot be
      confirmed or used. Nothing judged yet: judging the 24 nemotron outputs is GPT-6 quota
      and needs owner approval. Next step to confirm: generate fresh OpenRouter qwen3.8-27b
      and nemotron outputs for the same 24 episodes (48 requests) after the
      daily quota resets, through the worker's agy runner as well, and judge
      them the same way. Summaries are the weak field in every lane (37-79%
      unsupported, against 11-15% for facts): one wrong detail sinks a long summary. Next step: a shorter, fact-bound summary
      in the synthesis prompt, measured on the same 24 episodes. Also found:
      worker-lane records named the requested `qwen3.6:35b` whatever answered
      (fixed in `3504408`; a result without an executor now records `unknown`.
      Older records keep the wrong label, and so may a new record built from a
      kept partial saved before the fix; the truth is in the worker's
      `attempts` table). A different lever measured
      the same day: OpenJev, an open-weights decision model (MLX 4-bit, local,
      `~/models/openjev`), asked one yes/no "is this claim supported by the
      transcript" per fact. It scored all 8 invented claims from those runs
      0.20-0.84 and all 12 supported ones 0.92-0.98; a 0.9 cut gets 20 of 20 at
      ~1-3.5 s a claim. It is a candidate faithfulness gate on facts before ingest,
      whichever model generated them. The larger sample did not hold that
      result. It used 30 registry episodes and 341 claims, which GPT-6 labelled
      in one Codex call, marking 44 unsupported (qwen3.6 40 of 310, agy-gemini 4
      of 31). On the 81 claims OpenJev scored before the Mac froze, its AUC was
      0.86. A 0.6 cut flags 5 claims, all of them truly unsupported. A 0.9 cut
      catches 8 of 12 but flags 21 of 69 supported claims. Median ~12 s a claim.
      So it works as a precise flag, not as a gate. The freeze came from
      OpenJev MLX (~15 GB) running beside the worker's `qwen3.6:35b` (22 GB at
      131k context) and the session load. Never run the two together.
      Finished the same afternoon on nova (CPU, capped transient unit,
      client TTFB unaffected): all 341 claims give AUC 0.881. A 0.5 cut flags
      13 claims, 12 of them truly unsupported (92% precision), but that is only
      27% of the 44. A 0.9 cut catches 70% and flags 16% of the supported
      claims. It catches structural fabrication (`[~]` read as done, a refused
      command reported as run, an unshown cause) and misses subtle number and
      attribution errors. Decision input: at most a cheap flag at ~0.5 before
      ingest, not a faithfulness gate. Decided 2026-10-10 after a read-only
      GPT-6 review: do not wire it. Ingest indexes title, summary, facts and
      open ends as one text record (`atrium/ingest/to_synthesis_records.py`),
      so a per-claim flag changes nothing served. It also costs ~3 min per
      episode on nova, and the sample has no OpenRouter output. Reconsider only
      if it beats the baseline in the 20-30 episode comparison below. The
      artifacts, including `shim_llamacpp.py`, are in
      `~/p/wiki/atrium/evaluations/openjev-faithfulness-2026-10-10/` (local,
      git-ignored). The recipe is in the wiki at `brain/topics/openjev.md`;
      the owner holds a commercial licence.
      **Measured 2026-10-16** (same directory; GPT-6 via Codex judging blind, lanes
      mixed per episode in `judge_new/`). Fresh nemotron-3-super with the current
      prompt (24 outputs, `judge_or/`): 14.3% unsupported, summaries 19/24, facts 9.2%.
      The same model with a short, fact-bound summary (`gen_or_short.py`: 1-3
      sentences, at most 60 words, only outcomes the transcript shows, plus one
      system sentence): 6.8%, summaries 9/24, facts 3.0%. A second, blind judge from
      another family (Claude Sonnet, summaries only, `judge_summary_claude/`) agrees
      on direction: current 12/24, short 5/24, codex 2/24; it matched GPT-6 on 61 of
      72 summaries. New free models: `nvidia/nemotron-3.5-super-vl:free` (released
      2026-10-15) 15.1%, summaries 13/24; `nvidia/nemotron-3-ultra-550b-a55b:free`
      17.8%, summaries 15/23 -- neither beats the current one. The production codex
      lane (`gpt-6.1-sol`, low) 6.7%, summaries 2/24, facts 0/114, but Codex is last
      in the owner's routing order. DeepSeek has no free model on OpenRouter any
      more. **Adopted 2026-10-16 (owner):** the short summary description
      and system sentence are in `synthesis_schema.py` and `synthesis_prompt.py`. Existing
      records stay: a pass skips any episode a population already holds
      (`done_episodes`), whatever its job key. Next: read the first new records' summaries
      after the next pass, and watch the worker for old-prompt jobs left offered.
      **Outage found 2026-10-16:** no synthesis record from 2026-10-12 to 19:46 that day;
      every `atrium.tasks` job failed `runner_failed` (2,708) because agy stopped
      offering `gemini-3.1-pro-high` and the `claude-sonnet-5-5-high` fallback sat in
      cooldown. Profiles moved to `gemini-4-argon-high` (wiki `e7bdf9dbf`, unmeasured for
      faithfulness); worker `aa992c4` now prints an unmatched runner failure's tail;
      machine-job episodes (security reviews, Vexa, invoices) are no longer synthesized
      (`babafc9`). First argon records carry the new prompt, summaries 23-32 words. The first
      36 argon production records with the short prompt, judged blind by GPT-6
      (`evaluations/argon-production-2026-10-16/`): 9 of 261 claims unsupported (3.4%),
      summaries 1/36, facts 3.1%; the 11 that are not security reviews 6.0%. Argon's
      agy quota walled after ~50 jobs (cooldown ~3 h); the script then hands over to
      the local lane, which the worker's `local_idle_only` holds until the Mac is idle. Argon's
      quota turned out weekly ("Resets in 167h"); the worker now rests a walled model
      until the reset its message names (worker `6accfe1`, `b0dc0c6`), and `atrium.tasks`
      falls back to `atrium.agy-flash` (`gemini-3.8-flash-high`, wiki `0f4c18159`), which
      scored 9.1% unsupported with the short prompt (summaries 3/23). First Flash
      production records 20:59 on 2026-10-16, summaries 43-49 words.
      Spot-check 2026-10-17 of 10 random single-chunk Flash records (registry
      `model_resolved = agy-gemini-3.8-flash-high`, shown as `worker-atrium.agy` in
      `atrium status`) against the archive: 1 harness echo, 7 faithful, 2 with a false
      claim, both about the episode's outcome on the two longest transcripts (a review
      said to end without a verdict that ended "fix first"; a refactor said to end
      failing that ended green). 2/9 against qwen's 3/8; too few to call better.
      Report: `~/p/wiki/atrium/evaluations/flash-spotcheck-2026-10-17.md`.
## Promotion pipeline

- [ ] The claim ledger stores `project` as resolved at extraction time. It is
      derived from the index and cheap to recompute, so if the resolution rule
      changes again, rewrite the field rather than re-calling the model -- the
      first two rules changed 42 of 527 rows between them.

## Observability

- [~] **The prompt hook gets nothing under load, and the service keeps working for
      clients that left (2026-10-18).** Partly fixed 2026-10-19 by `9e9b462`: clients
      send `timeout_s`, and the service's `DeadlineReranker` ends every rerank at the
      client's deadline less `FINISH_MARGIN_S` (0.5 s), the 3 s budget still the upper
      bound (test `test_a_slow_rerank_stops_in_time_for_the_client_that_waits`, red
      without the change). Live at load 13-19 after the restart: 2 of 4 CLI calls served
      (4.8-4.9 s), 2 still `service_timeout`. What is left is the batch: the deadline is
      checked between batches only, and one batch of 4 took ~4 s at that load (rerank
      step 7,054 ms on a 7 s deadline). Measured at load ~13, 16 pairs: batch 1 total
      2.1-2.3 s, max batch 0.18-0.25 s; batch 4 total 1.9-2.0 s, max 0.52 s. Batch 1
      bounds the overshoot for ~10-15% more CPU on a rerank that completes. Smallest
      step: measure batch 1 vs 4 at load above 50 before choosing. Original entry: After the 19:06 restart (`09c354d`, `7758b81`),
      28 of 29 context calls returned `service_timeout` at the client's 7 s, while the
      service still ran retrieval and the rerank to the end: `ContextRequestHandler`
      only notices the peer is gone when it writes the result. In-process at load ~23:
      warm request 4.2 s, of which rerank 3.08 s (5 batches of 4, 0.6 s each) that
      exhausted the 3 s budget and was discarded (`rerank_unavailable_fused_order`);
      cold first request 14.3 s. Codex analysis (read-only, same day): pass the
      client's deadline to the server and check it, and peer closure, before retrieval
      and between rerank batches; keep the 3 s rerank budget (owner, 2026-10-18: no
      "skip if it will not fit" heuristic). CPU saving is small (under ~6 CPU-min/day);
      the point is a hook that answers. ORT defaults are already `ORT_ENABLE_ALL`,
      and `intra_op_num_threads=2` measured slower (3.39 s vs 2.38 s for 16 pairs), so
      neither is an easy win. Smallest step: a test where the client disconnects at
      7 s and the server stops at the next batch boundary.
- [ ] **Refresh stages report wall time, not CPU (2026-10-18).** Daily cost can only be
      bounded: roughly 19 passes a day of export ~6 min, import ~5 min, ingest ~1 min,
      doctor ~2 min, at most ~310 core-min/day if each held one core. Export and import
      dominate, and segment mode removes both (see the stage 3 entry above). Owner,
      2026-10-18: the refresh stays hourly. Smallest step: record user+system CPU per
      stage in `~/p/dotfiles/bin/atrium/atrium-refresh` so the cutover saving can be
      measured instead of estimated.

- [ ] **Cause of the 2026-10-15 orphan posting is unknown.** `words` held a posting
      for rowid 19395878, in neither `records` nor `words_docsize`, so every ranked
      query touching it raised "database disk image is malformed" and the context
      service answered `index_unavailable_or_incompatible`. `repair-index --apply`
      rebuilt both indexes (atrium `83b1498`; words check 30.5 s / rebuild 55.1 s,
      substrings 719.1 s / 564.8 s), and `doctor` now probes for it (`fts` check,
      ~3 s). The triggers (`schema.sql` `records_ad`/`records_au`) delete with
      `old.text`, so the shape the fixture reproduces -- a 'delete' whose text
      differs from what was indexed -- needs a path that changes `records.text`
      or the FTS outside them. Suspects, none proven: the erase path toggling FTS5
      `secure-delete` on and off around its deletes (`delete_erased_rows.py`), two
      SQLite builds writing one file (the release venv and another interpreter),
      or the forced refresh of 2026-10-14 after the forget pass rewriting 18,093
      records. Two suspects eliminated 2026-10-16: (1) erase has never run on the live
      index (no `erased-conversations.txt` in the state directory), so `secure-delete`
      was never toggled there; (2) Homebrew installed SQLite 3.54.0 on 2026-10-14 12:47,
      the day before, but tokenizing every seventh live record (67,233) through
      `unicode61 remove_diacritics 2` and `trigram` under 3.54.0 and under a bundled
      3.50.4 (`sqlean.py`) gives identical terms and offsets on every document, so a
      build change does not make a trigger's 'delete' miss what its insert indexed. No
      `INSERT OR REPLACE` touches `records` (whose implicit delete would skip the
      triggers). Left: the forced refresh rewriting 18,093 records, a path that only
      uses the triggers. Smallest step: when `doctor` next reports `fts_orphan_postings`,
      copy the index before repairing and bisect the refresh log for the last
      write between the two doctor runs.

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

## Measurement

## Integrations

- [!] Windsurf and Trae remain unindexable at layer 1, and not for an exporter
  bug: agents' `TODO_LOG.md` (2026-08-31) found Trae's dialogue store encrypted at
  rest and Windsurf's Cascade history server-side only; the bogus Trae records
  (VS Code picker state) were fixed the same day. Tracked in `~/p/scribe/TODO.md`
  (git-ignored there, so local to this Mac). **Blocked on:** decrypting Trae's
  store, and a server-side export for Windsurf if one exists.

## Self-improvement

## Cross-project

- [ ] Scribe (formerly `rocket-agents`), tracked in `~/p/scribe/TODO.md`: canonical event IDs are conversation-local in practice —
      `conversationEventFromRecord.ts:20` derives them from `event_index + text`
      with no conversation identity, and real cross-conversation collisions were
      measured (OpenCode, Cursor). Atrium works around it with
      `sha256(conversation_id, event_id)`; the canonical contract should carry the
      identity itself. It re-keys every archived event, so it lands with the v2
      stage 3 cutover.


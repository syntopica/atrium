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
  - [ ] Freshness after cutover: `archive_path()` stays the full materialized export,
    regenerated on every generation change, so `doctor` coverage and `recall` keep reading
    one file. Record the ingested generation id in the index; report stale when
    `scribe segments-inventory`'s `generationId` differs or `pendingDeliveries` > 0.
  - [ ] Workstream 4 support: rebuild a test index from `export-materialized` and compare
    raw records, both FTS lanes, synthesis records and vector identities against the live
    inventory, read-only against live.


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
- [!] **The `user` role carries tool output and machine prompts.** A 200k-rowid sample
      (2026-10-10, ~7.2k user records) by bytes: atrium synthesis prompts 23%, other
      records over 5k chars 20%, human-sized prompts 17%, tool-output-shaped text (Read
      `N<tab>` listings, `[TOOL ...]`, search results) 16.5%, `<tag>` harness text
      11.6%, the security-review template 7.4%, app batch prompts (Vexa classifier,
      invoice extraction) 3.8%, skill bodies 1%. Average user record 2,967 chars against
      288 for assistant. These bloat both FTS lanes and crowd lexical ranking. Smallest
      next step was to find the archive event kinds; found 2026-10-11: scribe's
      `conversationEventKindFromRecord` reads only `type`/`kind`/`payload.type`, and a
      Claude Code line is `type: "user"` with `tool_result` blocks in `message.content`,
      so the archive itself files it as `kind: message, role: user`. The fix is
      scribe's, and it changes content hashes, which the split froze until the v2
      cutover. **Blocked on:** scribe v2 stage 3; tracked in `~/p/scribe/TODO.md`
      ("Event classification"). The machine-prompt shapes (synthesis prompts, the
      security-review template, app batch prompts) are separate: most of the first are
      already gone with the `atrium-codex-*` exclusion.
      2026-10-14: the tool-output share no longer waits on scribe. Atrium `750ae09`
      and `5552415` reject a rendered `tool: <Name>` call and the unmarked results
      that answer it; the 18:30 refresh rejected 760,326 calls and 683,384 results and
      left 111,298 user and 300,790 assistant records (index 1,923,985 to 483,624). What
      remains here is the machine-prompt shapes; re-sample the user role before
      deciding whether this entry is still blocked.
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
- [ ] One JSONL rewritten in full on
      every import: 2.6 GB -> 3.36 GB in a day, and the 2026-08-31 recovery import
      took roughly 45 minutes to add 3,008 conversations. With an hourly refresh
      that is O(corpus) write amplification per hour to append a handful of
      conversations, and it gets worse monotonically. The archive is meant to hold
      everything forever, so the format has to stop being rewritten whole --
      segment by period or by source, or make append the normal path and the full
      rewrite a compaction. Cross-project: rocket-agents.
      Measured 2026-10-10 19:29-19:48: a 19-minute refresh to add 1 conversation and
      update 5 (export 7.1 min re-reading 47,957 artifacts, import 4.6 min rewriting the
      6.8 GB archive plus a 6.8 GB backup, ingest 3.6, ingest-synthesis 2.5, embed 1.2);
      refreshes start every 30-50 min, so the machine is refreshing about half the time.
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
      if the key's free headroom falls to 100. Next step to confirm: generate fresh OpenRouter qwen3.8-27b
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

## Promotion pipeline

- [ ] The subject/predicate/value triple is the suspect part of the claim
      schema: it degrades a quarter of the sample and adds nothing the sentence
      does not already carry. Consider replacing it with an `entities` list of
      quoted identifiers, which is what a merge actually needs, and keeping the
      sentence as the claim. Decide after the stage-three design lands, because
      the merge algorithm is what says which fields it needs.
- [ ] Spend the new 100-claim holdout once, on stage three's acceptance, not on
      stage two. Two failure shapes are already visible and neither is
      fixed by prompt-fiddling: a sentence carrying two assertions loses one
      (the Apache 503 claim kept "contains maintenance downtime" and dropped
      "now reads the title first"), and a claim whose sentence names no file or
      repository is classified `general` even when it is plainly about one
      project (`/findings expects to be an array`, in project-after). 64 of 498 came
      back `general`; that is the number to check by hand.
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
  Update 2026-10-10: 18 runs since the stage logging (2026-10-09 21:45 to
  2026-10-10 11:00), all 10-17 min, none slow. Typical split: export 4-7 min,
  import 3-4.5, ingest 3-3.5, ingest-synthesis 2, ingest-notes 12 s, embed 1-3,
  doctor 2. The slow window stays unexplained (2026-10-09 11:38-20:19 only);
  close as not reproduced if another week passes without a run over 30 min.
  Per-prompt retrieval (`--lane dense --limit 4`) measured 0.8-1.0 s warm,
  well inside the mod's 10 s budget.

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

- [~] **Lone harness echoes no longer cost a synthesis call (2026-10-10).** Measured over the
      registry: 2,468 single-event episodes, of which 2,126 are only "Structured output
      provided successfully" and 87 only "[Request interrupted by user]" (role `user`, the
      tail of a subagent session). `is_trivial_episode` skips exactly those echoes -- an
      exact-match set, not a length floor, after a Codex review showed a length floor drops
      a short real message -- and the pass prints them as "harness echoes not synthesized".
      A floor, not a fold: folding would re-key and re-pay the neighbouring episode.
      Remaining: the ~2,213 echo records already in the registry are still indexed and can
      surface in recall. Excluding them at `ingest-synthesis` needs each record's event
      text from the index and would make `status`/`doctor` report them as intended but not
      indexed, so it was not done; smallest next step is a per-record `excluded` reason in
      the served-record choice that status counts separately.

## Measurement

- [!] **Reranker: wins on both sets, too slow for the 1.5 s gate; the query prompt
      does not win.** Re-measured 2026-10-15 with the honest harness
      (`~/p/wiki/atrium/evaluations/retrieval-2026-10-15/e2e.py`: real
      `retrieve_context`, production weights, links, budget, limit 8; the
      2026-10-14 numbers used an oracle population and w=0.5 and are void). R/MRR
      on acceptance (85) | held-out (88, `holdout-2026-10-15`, judged and audited):
      production 0.28/0.12 | 0.43/0.29. Query prompts `search` 0.26/0.13, `qa`
      0.26/0.15: `QUERY_PREFIX` stays. Rerank of each population's 32 fused hits
      (`retrieve_context(reranker=...)`, atrium `4addedc`, off by default):
      bge-reranker-v2-m3 0.39/0.24 | 0.51/0.39 (gained 9/7, lost 0/0);
      gte-multilingual-reranker-base 0.40/0.25 | 0.51/0.41 (10/8, 0/1), at 256
      tokens 0.39/0.22 | 0.50/0.39; mmarco-mMiniLMv2-L12 0.35/0.19 | 0.48/0.38
      (lost 1/3). Rerank wall time alone (`latency.py`, 20 questions, Mac load
      9-15): bge 512 tokens p50 10.4 s / p95 12.6 s; gte 512 4.0/6.8; gte 256
      1.8/4.5; gte 256 top-16 0.9/3.3; mini 512 1.5/4.3. CoreML: 167 s vs 1.3 s on
      CPU (172 partitions), unusable. **Blocked on:** the owner choosing between
      ~2 s more per context answer for +0.08-0.11 R@8, a shallower rerank, or
      waiting for the p95 to be measured on an idle Mac. Smallest step: the
      owner's answer; then switch `CrossEncoder`'s defaults to gte at 256 tokens
      and enable it in the context service with the budget the owner picks.

- [~] Acceptance set — built; the measurement phase is unblocked. **Protocol decided
  2026-10-11 (owner):** GPT-6 labels, Claude audits a sample, rather than the owner
  labeling by hand. In progress in the instance state
  (`atrium/evaluations/acceptance-2026-10-11/`, private: `syntopica/atrium` is public):
  90 sources sampled from the index (35 recent, 35 old conversations, 20 notes; half
  `no-overlap`), GPT-6 writes one question per source, a candidate pool from the
  words/dense/auto lanes goes to a GPT-6 judge for other answering sources, then the
  audit. **Built and audited 2026-10-11:** `labeled.jsonl`, 85 questions (es 47 / en 38,
  conversation 65 / note 20, overlap 41 / no-overlap 44 by a mechanical two-shared-word
  rule, recent 32 / old 33). The judge read 1,402 pooled candidates: 13 `answers`,
  68 `partial`; 10 questions carry alternatives. Claude's audit (`audit.md`): 15/15
  gists supported by their source; q030, q036, q060 vague; two judge `answers` doubtful.
  **First baseline (`baseline.py`, R@10 / MRR@10 by source conversation, live index):**
  all: words 0.28/0.18, dense 0.20/0.10, auto 0.28/0.17. overlap (41): words 0.56,
  dense 0.27, auto 0.56. no-overlap (44): words 0.02, dense 0.14, auto 0.02. notes (20):
  words 0.10, dense 0.30, auto 0.10. So the 80% R@10 of the machine-extracted set does
  not survive human-shaped questions, and `auto` behaves as `words`: on no-overlap
  questions the OR-match lexical lane almost never comes back empty, so
  `search_hybrid` fuses and buries the dense hit (dense alone finds 6 of 44, auto 1).
  Same on notes. Next steps, each measured on this set: (1) the routing rule in
  `search_hybrid` (when to trust dense over a weak lexical match), (2) the notes-only
  FTS table below, (3) the dense-over-raw reserve lane (measured and kept unshipped
  2026-10-12, see `TODO_LOG.md`). Known defect in `baseline.py`:
  the `note` kind and `note` age share a group key, so that row prints n=40; rates are
  unaffected (fixed in `baseline.py`).
  **Routing, measured 2026-10-11 (`lanes.py`, `simulate.py`):** on the context surface,
  history keeps the 0.7 lexical weight (0.5 and 0.3 lose MRR) and the curated pass now
  fuses at 0.3 (`14aa1ab`): end to end 0.45/0.39 to 0.55/0.47 on the 20 note questions. A
  rule gated on the narrow AND pass does not help: it matches for only 12 of 85 questions.
  `search_hybrid` (the `atrium search` CLI) is unchanged: 0.5 gains R@10 (0.28 to 0.31) but
  loses MRR (0.17 to 0.15). Earlier text: The 365/389
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

- [!] Windsurf and Trae remain unindexable at layer 1, and not for an exporter
  bug: agents' `TODO_LOG.md` (2026-08-31) found Trae's dialogue store encrypted at
  rest and Windsurf's Cascade history server-side only; the bogus Trae records
  (VS Code picker state) were fixed the same day. Tracked in `~/p/scribe/TODO.md`
  (git-ignored there, so local to this Mac). **Blocked on:** decrypting Trae's
  store, and a server-side export for Windsurf if one exists.

## Self-improvement

- [ ] Query log, gap detection, and brain proposals. The durable-state
      contradiction this waited on was the Durability item, closed 2026-09-05
      (`TODO_LOG.md`) by replicating the synthesis registry through
      `sync-all-safe`; a query log would be a _second_ durable store that nothing
      carries yet. Resolve the placement rule first (brain, or an explicitly
      backed-up sidecar that the sync actually carries), then build; layer 2 must
      stay disposable, and as designed today a rebuild would erase it.

## Cross-project

- [ ] Scribe (formerly `rocket-agents`), tracked in `~/p/scribe/TODO.md`: canonical event IDs are conversation-local in practice —
      `conversationEventFromRecord.ts:20` derives them from `event_index + text`
      with no conversation identity, and real cross-conversation collisions were
      measured (OpenCode, Cursor). Atrium works around it with
      `sha256(conversation_id, event_id)`; the canonical contract should carry the
      identity itself. It re-keys every archived event, so it lands with the v2
      stage 3 cutover.

- [ ] **Bulk jobs on nova must be memory-capped.** Filed from the hosting
      ops repo (2026-10-12): the nova embedding run of 2026-10-11
      (`run_shards.sh`, 12 `nova_embed.py` shards at 5-8 GB RSS each) had a
      guard that watched output growth, not memory, and the kernel OOM-killed
      the host's MariaDB at 2026-10-12 04:10 UTC. nova serves production.
      Next step: any future run there goes in a capped transient unit
      (`systemd-run --scope -p MemoryMax=<n>G`) with a memory guard, or runs
      somewhere else.
      **Memory caps are not enough (2026-10-14):** two memory-capped experiment
      units (re-embed 1200% CPUQuota, rerank 1000%, Nice 10) held ~19 of 32 cores
      and Apache hit `MaxRequestWorkers` at 15:52 UTC: every site timed out for
      ~3.5 min until the units were stopped (`~/p/nubenode/TODO.md`, Server Ops).
      Daytime runs on nova get CPUQuota <= 400% in total, or run in the night
      window; check load and `MaxRequestWorkers` headroom before launching.

- [ ] **The context service is swapped out under memory pressure, so the
      prompt hook times out.** Observed 2026-10-12 ~18:55 local: the hook
      reported `context_service_timeout`; swap was 44.6 of 45 GB used, and
      `serve-context` (pid 1046) had 44 MB resident and 1.3 GB swapped or
      compressed. Direct socket requests took 0.2-0.6 s, but the first
      `atrium context --lane dense` after idle took 23 s (later ones 1.2-1.5 s),
      past the hook's 10 s kill. Holders at the time: Ollama `llama-server`
      24 GB (qwen3.6:35b, reloaded mid-pass), Backblaze `bztransmit` 17 GB,
      the `atrium synthesize --workers 4` Python process 14 GB (flat over
      20 s). Next step: find why the synthesis driver holds 14 GB (the model
      lives in Ollama, not in it), and decide whether `serve-context` should
      pin its working set (matrix and ONNX session) so it survives pressure.

- [ ] **The local synthesis lane finishes nothing and holds ~38 GB doing it.**
      `synthesis.log` on 2026-10-12: every local pass from 11:36 to 18:23
      ended `exit 124` (the 3300 s time box) or 143, with no `synthesized`
      line, and the 18:38 pass had printed only "13 conversations were left
      half done; walking them next" after 20 min. Each pass keeps qwen3.6:35b
      loaded in Ollama (24 GB) and a 14 GB driver process, then the next tick
      starts 15 min later. Next step: find why the half-done walk never
      completes a conversation (worker transport, `ATRIUM_LOCAL_TRANSPORT=worker`
      queue, or the model). The job was booted out on 2026-10-12 19:00
      (`launchctl bootout gui/$(id -u)/com.cristian.atrium-synthesis`); bring
      it back with `launchctl bootstrap gui/$(id -u)
      ~/Library/LaunchAgents/com.cristian.atrium-synthesis.plist` once fixed.

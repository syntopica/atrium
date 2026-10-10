# TODO

> Consolidated from the accessible Claude, Codex, Cursor, and Antigravity
> project history. Last reviewed: 2026-10-10. History coverage: Partial —
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

- [ ] **Per-prompt `--lane dense` blows the mod's 10 s budget under disk contention.**
      2026-10-10, MacBook: the `prompt.submit` mod reported `atrium-context: context
      unavailable ($.process.run(atrium) aborted: still running after 10000ms)` on every
      prompt; the same command measured 40-57 s at 19% CPU (cProfile: 26 of 28 s in
      `dense_hits`' one `execute`, the main thread in `pread` under
      `sqlite3BtreeTableMoveto`). The history scope for `~/p` is 60,082 vector-bearing
      records, and `sql/context/dense_hits.sql` reads every one of them in full, text
      included (112 MB of text plus 92 MB of vectors, then a temp B-tree for the
      `ORDER BY`), scattered over a 22 GB index, only to keep the top 4. Contention at the
      time: a concurrent `ollama pull gemma4:26b` (about 17 GB written), the 12:15-12:28
      refresh and four local synthesis workers. Once those ended the same call took 5.1 s
      at 96% CPU, still half the budget (it was 0.8-1.0 s on 2026-10-09 with a smaller
      corpus).
      Design study 2026-10-10 (Codex gpt-6-sol, read-only on the index, under a bounded
      2 GiB `F_NOCACHE` reader and 8 CPU workers; same top four on every path): current
      full-row scan 49-63 s, 6.6 GB of physical reads for 207 MiB returned; a compact
      float32 artifact of the 60,082 ids and vectors (92 MiB) ranked plus a four-row fetch
      in 0.10-0.13 s; a fresh-process first embedding 0.75-1.6 s. The two-phase query
      (ids and vectors first, text for the top four) measured 3.1-3.3 s there, but
      re-checked here it took 46.6 s when run first on a cold cache and 3.4 s for the
      full-row scan right after it: it only helps when the pages are already cached, so
      it is not the fix for saturation. A `(workspace, role, record_id)` index does not
      cover `vectors.vector`, which lives in another table.
      Recommended design: an exact float32 vector artifact (ids, vectors, role and
      workspace slices; no text) built from one WAL read snapshot, validated, published
      by atomic manifest replace, keyed to a dense generation counter that every
      record and vector writer bumps in the same transaction; served by one resident
      per-user process holding the embedder and the matrix, reached by the hook over a
      Unix socket, with an internal 7-8 s deadline that returns an explicit degraded
      answer before the hook's 10 s kill, and the hook surfacing degraded warnings
      instead of "nothing retrieved". Keep float32 (float16 kept the top four 32/32,
      int8 only 19/32). Smallest next step: the generation counter plus the artifact
      builder, then the service; acceptance is the real hook under a concurrent refresh,
      cold-ish cache, I/O and CPU load, recording p50/p95/p99 and degraded counts.

- [!] **A notes-only FTS table is worth building; enabling it waits on the acceptance set.**
      Re-measured 2026-10-10 (Codex, re-run and spot-checked here; artifacts in the instance
      state, `atrium/evaluations/notes-only-fts-2026-10-10/`): an external-content FTS5
      table over the 6,310 curated notes, same tokenizer as `words`, builds in 0.42 s at
      13.5 MiB. On 12 probe questions, the real `lexical_hits(curated=True)` against an
      unpruned OR on the notes table: median 146 ms vs 4.7 ms (27x), no budget
      exhaustion either way, top-5 holds the answering note for 5/12 vs 8/12 (three gained,
      none lost), median top-10 overlap 2/10. The low overlap is the bm25 statistics
      changing with the corpus, which is the ranking risk this item named. Twelve
      questions written from known note titles cannot license a ranking change, so this is
      blocked by the same condition as Measurement below: the hand-labeled acceptance set.
      Build plan once it exists: the table plus its triggers in the schema, refreshed by
      `ingest-notes`, behind the curated lane's broad pass only, compared on that set.

- [!] Dense-over-raw stays an explicit reserve lane: even with an oracle
  embedder the zero-lexical-overlap class recovers only 3 of 25 from synthesis
  alone. "No ANN" is not approved until the reserve lane is measured at full
  corpus scale. Blocked by the same condition as the Measurement item below
  (2026-09-01): the only question set is machine-extracted, and this item
  exists precisely to justify a production decision ("no ANN"), which that set
  cannot do. Smallest unblock: the hand-labeled set, then the measurement is
  hours of embed CPU plus the existing eval harness.

## Ingest / Store

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
  filed there as `~/p/agents/TODO.md:351`; this entry tracks only Atrium's side, the
  per-writer cursor for incremental ingest, which waits on that format.
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
      it answered with `think: "low"`. Next step: a 20-30 episode sample judged
      against GPT-6 before changing the local model.

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

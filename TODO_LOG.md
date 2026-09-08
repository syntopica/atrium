# TODO Log

> Searchable record of closed project work. Active work lives in `TODO.md`.

## 2026

### 2026-09

- [x] 2026-09-08 — **Ingest / Store:** **Session scratchpads are indexed as if they were projects.** Paths like
  `/private/tmp/claude-501/-Users-cristiandeluxe-p-agents-tools/<uuid>/scratchpad`
  carry a `workspace` and become their own workspaces in the index — found
  2026-09-01 while folding renames. They are per-session temporary directories,
  not projects: they inflate the workspace count that made coverage read 2.1%,
  they never match a live `project_workspace`, so nothing can ever recall them,
  and their content is scratch. Either map a scratchpad back to the project
  whose name it encodes (the path contains it) or drop the workspace entirely
  at ingest, but not silently keep them as phantom projects.
  Done 2026-09-08 (`7e0ca9b`): mapped back, not dropped. The encoding replaces `/`, `.` and
  spaces alike with a hyphen, so the decode walks the real directory tree rather than
  splitting on hyphens -- which would have invented `p/inbox/companion` beside the real
  `p/inbox-companion`, the same phantom under another name -- and answers None when two real
  directories encode identically. Measured against the live index: 67 scratchpad workspaces
  collapse to 19 real projects, 331 conversations remapped, 45 dropped because their project
  directories are gone from disk (filed separately). 14 tests; the symlinked-project case
  (`~/p/iriscaceres -> /Volumes/iris-cs/iriscaceres`) is one of them, because the obvious
  `resolve()` guard against the encoded-prefix ambiguity rejects exactly that correct decode.

- [x] 2026-09-08 — **Integrations:** Nothing checks that Atrium's own documented entry points resolve, on either machine.
  `doctor` proves the index would answer, and proved nothing about whether a caller can ask.
  The same class of gap covers the `atrium-mcp` server, which both `.claude.json` files spawn as
  `uv run --extra mcp --directory ~/p/atrium atrium-mcp`. Smallest action: have `doctor` (or
  `atrium-refresh`, which already runs hourly) assert `command -v atrium` and that the MCP entry
  point starts, and report a machine where either is missing.
  Done 2026-09-08 (`bd9dfba`): `doctor` gained an `entrypoints` check, first in the run. It
  asks the question of a login shell's PATH rather than its own -- every documented route runs
  the doctor through `uv run --project ~/p/atrium`, which prepends `.venv/bin` where the
  console scripts exist by construction, so the inherited PATH answers yes even during the
  outage. Resolution follows the shell: candidates classified as directory / not executable /
  broken symlink / runnable, the scan continues past an unusable one, a shadowed-but-working
  wrapper is a warning. The directory case is the `bootstrap.sh` regression, and `shutil.which`
  is blind to it. The MCP half asserts the console script is declared, its module resolves and
  the `mcp` extra survived into the installed metadata, and says "declared, not started" --
  the server is stdio and the hosts spawn it in a different environment, so starting it here
  would prove nothing. Live on this machine: `ok entrypoints <macbook-host>.local:
  atrium resolves at ~/.local/bin/atrium; atrium-mcp is declared, not
  started`. 22 tests.

- [x] 2026-09-08 — **Durability:** **The drip's own scripts live only in `~/.local/share/atrium/synthesis/`.**
  `drip-loop.sh`, `drip-quota.py`, `drip-guard.sh` and `lane.env` are the bulk
  synthesis producer's whole control surface -- which lane runs, which quota
  gates it, what kills a hung pass -- and they are in no repository, on the
  same single disk as the registry, replicated by nothing. Two of them were
  rewritten twice on 2026-09-04 and the only copies of the previous versions
  are `*.bak-*` files beside them. Same class as the registry item below, and
  cheaper to fix: they belong in `~/p/dotfiles/bin` (or this repo) with the
  live paths as symlinks, so a lane switch is a reviewable commit rather than
  an unrecorded edit on one machine. Not done during a running pass.
  Closed 2026-09-08: all four are already versioned at `~/p/dotfiles/bin/atrium-drip/`
  (`98559d9` there, worker count sized in `97e0e7d`) with a README, and the live paths under
  `~/.local/share/atrium/synthesis/` are symlinks into that directory — verified with `ls -la`
  while a pass was running, and `git status` on `bin/atrium-drip/` is clean. A lane switch is now
  a reviewable commit, which is what the item asked for.

- [x] 2026-09-05 — **Observability:** **The curated notes were never re-indexed, so each machine's brain memory froze.**
  `atrium-refresh` ran `ingest`, `ingest-synthesis` and `embed` but not `ingest-notes`, which
  was left to be run by hand -- so a machine's brain index sat at whatever commit it last
  saw while the notes themselves moved on. Measured 2026-09-05 with both checkouts at the
  same commit: 268 notes indexed here against 243 on the mini, and this machine's own index
  was 268 notes stale before the manual catch-up. The notes are half the dense lane, so a
  frozen brain is a quietly worse `atrium search` with nothing on screen to say so. Fixed by
  adding the step to the refresh (33 s, incremental, skips unchanged notes) in
  `~/p/dotfiles/bin/atrium/atrium-refresh` (`280c432` there). The same commit versions
  `atrium-refresh`, `atrium-lock` and `watch-mtime.sh`, which had lived unversioned in
  `~/.local/bin` and been copied between machines by hand -- which is how the two came to run
  different pipelines at all -- and points `~/.local/bin` at them by symlink on both.
  **Adding the step exposed the deeper cause, fixed in `05ae293`:** the ingest read files the
  brain repository ignores. `inbox/` (its own SCHEMA calls it a scratch drop-zone "emptied
  after ingestion"), `reviews/` and `tools/offers/reports/` are all gitignored generated
  output, and 49 such files were in the dense lane as if they were curated knowledge -- 44
  raw newsletter-triage dumps among them. Being untracked they also differ per machine, which
  is the whole reason the two counts could not converge. `read_notes` now skips what the
  notes repo itself ignores, which is the right unit: an exclude list cannot express it,
  since brain ignores `tools/offers/reports/` while `docs/reports/` is curated content, and
  it would need editing on every new ignore rule. `--exclude` stays for raw subtrees a repo
  does track, which is what `sources/` is. Verified 2026-09-05: both machines index the
  identical set of 219 notes, diffed id by id.

- [x] 2026-09-01 — **Observability:** **Coverage was being measured against the wrong denominator.** "9.9% of
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

- [x] 2026-09-08 — **Integrations:** **`atrium` was not on PATH, so the documented command did not exist.** The console script
  is installed only inside `~/p/atrium/.venv`, while the global agent guidance tells every
  session to run `atrium search "<question>" --project .` — which answered
  `command not found` on any machine that never activated that venv. The index was healthy the
  whole time (1,252,652 records, `doctor` all-green, 44,076/44,076 conversations indexed), so
  this was a live memory that no agent could reach by the only route it was told to use, and it
  fails in the one way nobody reports: a session simply improvises instead. Only the helper
  scripts `atrium-lock` and `atrium-refresh` were linked into `~/.local/bin`; the CLI itself
  never was. Fixed on the Mac mini 2026-09-07: `dotfiles/bin/atrium/atrium` wraps
  `uv run --directory ~/p/atrium atrium "$@"` — the same call `atrium-refresh` already makes —
  symlinked as `~/.local/bin/atrium` (dotfiles `9408859`). Verified from an unrelated directory
  in a fresh login shell.
  **That first wrapper was itself wrong, and a Codex review caught it the same day.**
  `uv run --directory` changes the caller's working directory, so the `--project .` the guidance
  prescribes resolved to `~/p/atrium` and every scoped search silently answered from the wrong
  project — a worse failure than `command not found`, because it returns plausible results.
  Fixed in dotfiles `5439c53` with `uv run --project "$HOME/p/atrium"`, which selects the
  environment without moving the cwd. Verified from `~/p/brain`: `--project .` now hashes
  identical to an explicit `--project ~/p/brain` and differs from `--project ~/p/atrium`;
  before the change it matched the atrium one exactly. A second install bug went with it —
  `dotfiles/bootstrap.sh` linked every top-level `bin/*` entry, so a fresh machine got
  `~/.local/bin/atrium` pointing at the *directory*, shadowing the wrapper and installing none
  of the scripts inside it. Closed on the MacBook Pro 2026-09-08: the symlink is in place
  (`~/.local/bin/atrium -> ~/p/dotfiles/bin/atrium/atrium`, the `uv run --project` version) and
  `atrium search "test" --project .` from `~/p/brain` returns brain hits, so the cwd bug is gone
  on both machines.

- [x] 2026-09-05 — **Durability:** **The synthesis registry is replicated since 2026-09-04/05.** It held 17,456
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


- [x] 2026-09-04 — **Durability / Observability:** The Mac mini runs Atrium; MemPalace
  retired from it; the empty synthesis record found and refused.
  - Mini before: no `~/p/atrium`, no index, no registry copy, MemPalace daemon
    still mining 26 GB, `cleanupPeriodDays` unset (30-day session purge live),
    `~/.claude/settings.json` carrying the retired hooks and re-injecting them
    into `dotfiles` on six of eight daily runs. After: checkout + `uv sync`,
    hooks, `atrium-refresh` + `atrium-lock` + hourly LaunchAgent, aliases,
    registry copy (29,989 records -- the second disk the Durability item
    lacked), first full pass launched under a stall guard on `refresh.log`.
    Dotfiles fix (`a2ee1a5`): per-host snapshots under `claude/hosts/`, the
    template written by the primary only, `claude-apply` leaves an established
    host alone, import retry on `ConversationArchiveChangedError`, backup prune
    after every applied import, config push from the primary only, and a
    `macbook` leg for the secondary; mini schedule moved to 20:00.
  - MemPalace copy: 28.07 GB, 1,475 files, at
    `~/.local/share/mempalace-macmini-retired-20260904/`; verified by rsync
    itemize (clean), `integrity_check` ok on all four sqlite files, and the
    live palace's 464,413 embeddings intact. Its 6,755 mined sources were
    checked against the archive by session filename: 1,875 absent, all of them
    subagent transcripts (1,054), `memory/` notes (228), `tool-results/` blobs
    (590) or neo root paths (3) -- zero top-level sessions, so nothing to
    rebuild. Then daemon booted out, plist deleted, tool uninstalled, MCP entry
    removed, store deleted (26 GB reclaimed, 357 GB free).
  - The `1 NOT IN INDEX` on 77 consecutive refreshes was record
    `0514a5475b5b…` (episode `18e5771b225ee012d8cb6937`, `gpt-5.6-terra-low`):
    the producer answered `{"title": "", "summary": ""}` and the empty output
    was persisted, so it counted as intended, blocked every later population,
    and produced no index row. Quarantined to `records.empty-20260904/` on both
    machines; `synthesize_conversation` now raises `EmptySynthesisError`
    instead of writing such a record (`tests/test_synthesize_conversation_empty_output.py`).
  - Evidence: `atrium doctor` all ok at 16:54; `sync-all-safe.log` (conflicts
    08-28..09-03, `synced macmini` 09-01..09-04); mini `first-run.out`,
    `refresh.log`; palace comparison in the session scratchpad.

- [x] 2026-09-01 — **Retrieval:** Four renamed projects got their history back.
  - A rename splits memory the way the missed `[HOME]` redaction did, but more
    quietly: nothing in the archive records that a directory was renamed rather
    than deleted while an unrelated one appeared. Only a person knows.
    `workspace-aliases.json` (hand-maintained, `~/.atrium/`) folds the old name
    onto the current one at ingest, subdirectories included.
  - **Detection matters as much as the mechanism.** Timestamp contiguity alone
    is useless — it proposes the cross-product of every dead project ending
    near every live one starting, including `vexa-enrichment-backfill ->
    brain`. What works is content: the known-true rename shows `provertly`
    mentioned **7,522 times** by `verticagtm` against 46 by the runner-up, a
    163:1 dominance. Weaker ratios (2:1 to 4:1) are suggestive only, so the
    candidates were put to the operator with their evidence rather than
    applied. `smart-sales` was offered and declined — the signal came only from
    `brain`, which documents everything.
  - Folded, confirmed by the operator: `provertly -> verticagtm`,
    `agents-tools -> rocket-agents`, `smartfactu -> intelifactu`,
    `vexa-enrichment-backfill -> vexa`.
  - Result after re-ingest of both raw and synthesis records: rocket-agents'
    history starts 2026-06-26 instead of 2026-08-19 and its episodes reach back
    to 2026-08-13; intelifactu starts 2026-01-16 instead of 2026-04-14;
    verticagtm 2026-06-14 instead of 2026-07-12; vexa gained a 1,017-
    conversation day. No old name survives anywhere in the index.
  - Evidence: `tests/test_workspace_aliases.py` (9 tests); suite 149 passed.

- [x] 2026-09-01 — **Synthesis:** The producer moved to the Codex lane, and the
  unit of work moved from "the corpus" to "a project".
  - **Lane**: `gpt-5.6-terra` at low effort, chosen by measurement and a blind
    judge (`docs/studies/synthesis-producer-bench.md`). Production evidence:
    1,819 episodes synthesized across three passes with **0 failed
    conversations**, against `failed=30620` on the walled agy lane's last pass.
  - **Cost, measured off the quota needle**: one weekly percentage point buys
    ~187 episodes, so the window is ~18,700 and the ~150,000 remaining episodes
    are about eight weekly cycles. The cheaper model buys speed and reliability,
    not a finished corpus.
  - **So the goal changed.** Coverage by conversation (9.9%) was the wrong
    denominator: 13,162 of 13,269 workspaces hold under five conversations.
    Against projects with >=20 it is 71%, and the projects genuinely missing
    memory are about fifteen. `synthesize --project/--workspace` fills one at a
    time; `status --coverage` names them.
  - **Demonstrated**: `contratos` went from no memory at all to a real
    session-start recall block (six episodes, correct language, specific
    titles) inside one bounded pass.
  - **Supervision that earned itself**: a time guard stopped the pass at
    08:15:01, ahead of the agy drip waking at 08:22. Two producers overlapping
    both claim the same pending episodes and pay for each twice — which the
    registry audit shows already happened once, to all 383 Max-lane episodes.

- [x] 2026-09-01 — **Retrieval:** A project's memory was split across two
  spellings, and half of it was unreachable from inside the project.
  - Found while measuring which projects actually gained memory: 29 projects
    existed in the index under both `[HOME]/p/x` and `/Users/<name>/p/x`, with
    **4,053 conversations under the unredacted spelling**. `project_workspace`
    resolves a live cwd to the `[HOME]` form and every lane prefix-matches on
    it, so that half answered nothing — 1,331 of intelifactu's conversations,
    a third of the project, invisible from inside intelifactu.
  - Cause is upstream: the exporter's `[HOME]` redaction missed those
    conversations, which also put the real username into a field the redaction
    existed to clear. The archive is canonical and is not rewritten, so the fix
    belongs in the derived index: `canonical_workspace` folds a real home path
    back to the marker at ingest. The next full ingest rewrites the affected
    conversations, because the stored workspace now differs from the new one.
  - Evidence: `tests/test_canonical_workspace.py` (7 tests, including the
    `/Users/someone-else` prefix trap); suite 133 passed. Filed upstream in
    `~/p/rocket-agents/TODO.md`.

- [x] 2026-09-01 — **Observability:** Fixed the staleness warning that the
  staleness reporting itself created.
  - Adding the refresh age to `atrium status` made every hourly `refresh done`
    line in `~/.local/state/atrium/refresh.log` report the run as
    `<- STALE`: `~/.local/bin/atrium-refresh` ran `atrium status` *before*
    writing its completion stamp, so status always read the previous run's,
    one whole interval old. A warning on every single run is one nobody reads
    — the exact failure the observability group exists to prevent, introduced
    by the fix for it.
  - The stamp now precedes the status call. The pipeline's work is finished at
    that line; status only describes it, and a failing status no longer erases
    the record of ingest and embed having succeeded. The script is untracked
    local tooling, so a timestamped copy was kept beside it before editing.
  - Evidence: `sh -n` clean; the next scheduled run's log line will carry the
    ages without the marker.

- [x] 2026-09-01 — **Observability:** `atrium doctor`'s coverage check stopped
  warning about a permanent, expected class.
  - It warned "528 missing" on every run. Measured against the live archive:
    all 528 legitimately admit zero records — every event in them is a tool
    call, a system notice or a bare acknowledgement, which is the admission
    rule working. Real drift was zero. A check that warns every run is how an
    operator learns to ignore warnings, which is the failure this whole group
    of items exists to prevent.
  - Coverage is now measured against the conversations that *can* be indexed:
    `read_archive_admissions` streams the archive once and returns both sets
    (the admission test is nearly free — the line is already parsed for its
    id, and `to_records` is a generator, so it stops at the first admissible
    event). The zero-admission count is still printed, because a number that
    moves is worth seeing; it just is not a defect.
  - Evidence: live `doctor` now reports `30318 of 30318 indexable
    conversations indexed, 0 missing, 0 indexed but not archived, 528 archived
    conversations admit no record` — all six checks ok, 88s over a 3.4 GB
    archive. `tests/test_doctor.py` 10 tests; suite 120 passed.

- [x] 2026-09-01 — **Observability:** The capture-versus-deletion window is
  measured, and the deletion cycle that cost 7,638 sessions is identified and
  already closed.
  - **The cause was Claude Code's own retention.** `cleanupPeriodDays` defaults
    to 30 days, and that is the cycle that emptied `~/.claude/projects` between
    exports. It is set to `99999` in both profiles — verified live and in the
    dotfiles source (`claude/settings.json`, landed `87c097d`, 2026-08-28,
    three days *after* the loss and by auto-sync rather than by decision).
    `~/.claude-second-profile/settings.json` symlinks to the personal file, so one
    value covers both quotas.
  - **Measured evidence that nothing is deleting today**: the oldest surviving
    Claude transcript is 2026-04-01 (five months, far past the 30-day default);
    4,772 session files, 659 of them older than 30 days. Codex keeps 16,476
    rollouts with 240 older than 60 days. Cursor stores conversations in a
    SQLite DB with no per-conversation expiry.
  - **Verdict**: the shortest active deletion cycle across every captured
    provider is now *none*; the refresh runs hourly with a 15-minute floor plus
    a session-end trigger. One hour against an unbounded retention is provably
    ahead, so the class is closed — by measurement, not by assumption, which is
    what the item asked for.
  - **Residual, filed in `~/p/dotfiles/TODO.md`**: nothing asserts the setting
    stays high. It is a plain value in a synced JSON file, and the same
    auto-sync that set it could revert it; a bootstrap against an older source
    would restore the 30-day default silently. Enforcement belongs to dotfiles,
    which owns that file — Atrium must not read provider configuration.

- [x] 2026-09-01 — **Observability:** `atrium status` says how stale it is, and
  recall complains instead of staying silent over a dead archive.
  - Result: every `status` now prints the archive's age, the last finished
    refresh, and the gap between the newest indexed content and now, with a
    loud `<- STALE` / `<- BROKEN` marker past the doctor's thresholds; the
    session-start recall block prints a `memory may be stale` warning when the
    archive or refresh is unhealthy — including when the block itself would be
    empty, which is exactly the case nothing else reports. New
    `atrium/doctor/newest_content_gap.py`; stamp and archive paths injectable
    for tests.
  - Evidence: `tests/test_status_staleness.py` (6 tests), suite 102 passed;
    live `atrium status` prints `archive last written 459s ago / last refresh
    finished 253s ago / newest indexed content authored 726s ago`.

- [x] 2026-09-01 — **Observability:** Both ingests report what they admitted
  per role and what each admission rule rejected.
  - Result: new `atrium/ingest/admission_tally.py`; `to_records` takes an
    optional tally and counts `kind <x>` / `role <x>` / `empty or
    acknowledgement` / `missing event id` rejections; ingest prints
    `admitted:` and `rejected:` lines ranked by count. The 162,225 tool-call
    records the mempalace recovery mis-filed would now be the first line of
    output. `ingest-notes` gained the same lines after the wave review caught
    it missing: files skipped as hidden or excluded are counted per rule.
  - Evidence: `tests/test_admission_breakdown.py` (4 tests); suite 118 passed.

- [x] 2026-09-01 — **Observability:** `atrium status` names every synthesis
  population and how many episodes of each the index serves.
  - Result: new `atrium/synthesize/population_report.py` and
    `choose_served_records.py` (chooser extracted from `_ingest_synthesis`,
    now shared, so status reports exactly what ingest would serve). Rows
    carry records/episodes/served, flag models missing from the active
    recipe, and mark a population serving zero episodes with
    `<- SERVES NOTHING`. The wave review hardened it twice: `intended` (what
    the manifest would serve) is now printed beside `indexed` (episodes the
    index actually holds), so an ingest that never ran shows as
    `<- N NOT IN INDEX` instead of hiding inside a recomputed count; and
    status reads the recipe through a non-writing reader
    (`read_recipe_priority`), so inspecting the system can never create the
    manifest the next ingest obeys.
  - First live run: `claude-sonnet-5` (the 383-episode Max-lane tranche,
    4.7M input tokens) serves 0 episodes — fully shadowed by
    `codex-cli-default`, which covers every episode it has. Expected under
    the priority, but now visible instead of assumed. Status now costs ~7s
    (one registry pass, ~16k records).
  - Evidence: `tests/test_population_report.py` (4 tests); suite 109 passed.

- [x] 2026-09-01 — **Observability:** The no-op refresh invariant is in the
  suite as the general property, not just the pinned vector case.
  - Result: `tests/test_noop_refresh.py` runs the ingest + ingest-notes chain
    twice over byte-identical inputs with the semantic layer fully embedded,
    and asserts the second pass leaves no trace: identical rowids (a rewrite
    would bump them), identical revisions, no lost vectors, nothing pending
    to re-embed. The hourly re-embed regression (19,198 vectors/hour of CPU)
    cannot return without this failing.
  - Evidence: suite 110 passed.

- [x] 2026-09-01 — **Security:** Untrusted-origin content is marked at ingest
  and can never travel unmarked into an agent's context.
  - Result: `ingest-notes --third-party` stamps records with role `source`
    (kept out of `SEMANTIC_ROLES`, so never embedded and never in semantic
    fusion); recall serves synthesis only, so no session-start injection;
    `Hit` now carries `role` through every lane, and search output prints
    `UNTRUSTED THIRD-PARTY TEXT` on source hits. Boundary documented in
    AGENTS.md as a hard rule. Third-party content is not ingested today
    (brain's `sources/`, 10,934 files, is excluded); this closes the path in
    advance of it. No schema change, no index rebuild.
  - Decision: Codex adjudication chose role/provider tagging over an `origin`
    schema column (high confidence; a column would cost hours of re-embed per
    machine or migration logic the disposable-index design avoids). Brief and
    verdict: scratchpad `decision.md` / `decision.json`, `codex exec -s
    read-only --output-schema`.
  - Evidence: `tests/test_third_party_origin.py` (5 tests); suite 115 passed.

- [x] 2026-09-01 — **Integrations:** "Thin adapters over the CLI core: MCP
  server and per-agent hooks" — verified already built, not rebuilt.
  - Result: `atrium/adapters/mcp_server.py` serves `atrium_search` and
    `atrium_recall` over stdio by calling the same `search`/`recent_episodes`
    the CLI uses (read-only annotations, bounded limits); registered in the
    personal profile's MCP list. Per-agent hooks:
    `~/.claude/hooks/atrium-recall.sh` (SessionStart injection) and
    `atrium-refresh-on-session-end.sh`, both thin shells over the CLI. The
    adapter never became the engine: `mcp` stays an optional extra and the
    core imports nothing from it. This session's CONNECTION_CLOSED was the uv
    resolution outage, not the adapter; import verified clean after the fix.

- [x] 2026-09-01 — **Integrations:** Remote-export adapter family designed
  before the local-file assumption hardened further.
  - Result: spike at `docs/designs/remote-export-adapter-family.md`. Grounded
    in current vendor reality (both ChatGPT and Grok ship official JSON
    account exports; neither has a consumer API): a content-addressed inbox
    of vendor ZIPs, vendor-specific parse, then the shared redaction and
    manifest path with `complete:false` and per-source `exportedAt`
    staleness. Scraping explicitly last. Implementation filed in
    `~/p/rocket-agents/TODO.md` (Conversations export) with the smallest
    next step: request both exports and write the ChatGPT parser against a
    real `conversations.json`.

- [-] 2026-09-01 — **Synthesis:** "Session-start injection with frozen-snapshot
  discipline" — superseded by the live SessionStart hook.
  - The injection exists and runs: `~/.claude/hooks/atrium-recall.sh` injects
    `atrium recall` output at every session start (verified live this run,
    including its honest failure block during the uv outage). The
    frozen-snapshot half was deliberately rejected in the hook's own header:
    recall is deterministic given the index and runs in ~1.2s with no
    embedder, so a snapshot file would add a staleness window and a writer
    for no measured gain — revisit only if recall ever needs the dense lane.
    The ~900-token budget is enforced in `render_snapshot`
    (`_BUDGET_CHARACTERS = 3600`), and the staleness warning added this run
    rides the same block.

- [x] 2026-09-01 — **Tooling:** The quality-baseline adoption briefly made uv
  resolution unsatisfiable, taking the MCP server and hourly refresh down;
  fixed at the source by the baseline rollout session.
  - Result: `busirocket-baseline-py` needed Python >=3.12 against this
    project's >=3.11; every plain `uv run` failed, so `atrium-mcp` died at
    connect and `atrium-refresh` failed after its export step. baseline-py
    0.1.3 published with >=3.11, lock updated (`1e55c25`). Coordinated live
    with session baseline-5a: config files stay with the rollout;
    code-level ruff/mypy findings belong to this backlog. Never hand-edit
    `.baseline-py-baseline.json`; `uv run baseline-py baseline update`.
  - Evidence: `uv sync` clean; `uv run atrium status` works; refresh log shows
    a completed pass minutes after the fix.

### 2026-08

- [x] 2026-08-31 — **Durability:** The archive stopped being one copy on one
  disk, and stopped being able to lose conversations quietly.
  - Result: `sync-conversations` had driven both the archive and its own
    scratch state from one path under XDG state, so it had been replicating an
    empty directory since the archive moved to XDG data on 2026-08-27. The two
    namespaces are separate now — durable data under `.local/share`, ephemeral
    locks and transfers under `.local/state` — and the orchestration test
    asserts the archive is not under state, so the defect cannot return
    quietly (`dotfiles 3f3737d`).
  - Two P0s in the importer, both silent (`rocket-agents 9e4d1f5`). It had no
    claim on the archive: two writers each read a revision, each renamed their
    own result over it, and the later one won. It now records the revision it
    merged from and refuses to publish if the archive moved, inside a lock held
    only for the verify-and-rename; correctness rests on the revision check,
    which has no staleness to adjudicate. And the merge was last-writer-wins,
    which between two archives is simply wrong — neither supersedes the other.
    It now uses the union merge that already existed for capture fragments,
    made commutative so both hosts converge on the same record either way.
  - **The merge fix earned itself the same day.** Capturing the Mac mini's
    corpus produced three conversations present on both hosts with differing
    revisions. One of them, `f35e12570c48`, had 353 events on the mini and 356
    on the laptop: importing it under the old `replace` would have destroyed
    the three events only this machine held. After the import it has 356.
  - The Mac mini's own history is captured: 7,697 conversations exported
    (`complete:true`, nothing skipped), of which **437 existed nowhere else**.
    Its 3,072 Claude session files were never 3,072 conversations, as the
    review warned — the export spans every source on that host, and the two
    machines' corpora overlap heavily because `~/.claude/projects` is synced.
    Archive: 26,598 -> 27,036 conversations, integrity verified against its own
    manifest.
  - An immutable snapshot lives on the Mac mini at
    `~/.local/share/rocket-agents/conversations/snapshots/2026-08-31-post-mempalace-recovery/`,
    mode 0400, sha256 matched on both hosts, and that machine runs Backblaze —
    so the archive now exists in three places rather than one. Its disk has
    FileVault off, which Backblaze does not change: that protects against loss,
    not against physical theft. Operator informed and accepted.
  - Evidence: `rocket-agents 9e4d1f5` (26 tests), `dotfiles 3f3737d`
    (`./scripts/check` green, no leaks), both hosts on the same commits via
    git bundle without touching GitHub, and the Mac mini runs the new
    concurrency tests green.

- [x] 2026-08-31 — **Cutover:** `~/.mempalace` deleted; 118 GB reclaimed.
  - Result: free space went from 272 Gi to 343 Gi. Deleted only after every
    part of it was accounted for: the 3,008 conversations that existed nowhere
    else are in the canonical archive, the knowledge graph is a file in brain's
    inbox, the purge export held base64 blobs and dirty checkpoints discarded
    on purpose, and the five palace backups were subsets — the largest
    divergence yielded zero sessions the archive does not already hold.
  - Checked before deleting rather than after: no process held the directory,
    no LaunchAgent referenced it, and the plugin was already disabled.
  - Operator directive: the store was not wanted for anything except what could
    be exported and reused.

- [x] 2026-08-31 — **Recovery:** Conversations that survived only inside
  MemPalace, rescued before the store is deleted.
  - Result: 7,638 Claude Code session files had been mined into MemPalace and
    then deleted from disk before any canonical export saw them; grouped by
    session that is **3,008 conversations**, and they existed in exactly one
    place. Rebuilt in rocket-agents' export format and imported into the
    canonical archive (`added: 3008, duplicates: 0, updated: 0` — nothing
    overwritten), taking it from 23,518 to **26,526 conversations**. Atrium
    picks them up on ingest; they carry their real workspace, so project-scoped
    recall reaches them.
  - The honest number is **19,705 prose messages**, not the 181,930 the first
    pass produced. MemPalace stored a whole turn as one blob with the role as a
    `USER: ` prefix and tool calls, tool results and thinking serialized inside
    the message text, so taking it at face value filed 89% of every recovered
    session as conversation — exactly the serialized tool output the admission
    rule in `to_records.py` exists to keep out. Decoded back into real kinds:
    65,186 tool-call, 65,129 tool-result, 31,623 reasoning, 19,705 message. The
    machinery stays in the archive with an honest kind and out of the index.
  - **2,692 redactions applied** on the way through, using rocket-agents'
    `redactSensitiveText` rather than a reimplementation. MemPalace did not
    redact; this content would otherwise have carried secrets straight into the
    canonical archive, which is the failure `AGENTS.md` cites as the reason the
    ingest may never read provider paths directly.
  - Two traps worth keeping: `JSON.stringify` leaves U+2028 and U+2029 raw, and
    they are JavaScript line terminators, so 5,596 records first arrived at
    rocket-agents' line parser split in half and failed schema validation --
    a latent hazard in its own exporter, not only in this recovery. And the
    same session appears under several project directories, so 7,638 source
    paths carry only 3,008 sessions; a record per path collapses to one at
    import and silently drops the rest.
  - Nothing else in MemPalace is worth keeping: the knowledge graph is exported
    to brain's inbox, the purge export holds base64 blobs and dirty checkpoints
    that were discarded on purpose, and the five palace backups are subsets --
    the largest divergence, 784 sources in `pre-rebuild-20260824` absent from
    the live palace, yields **zero** sessions not already in the archive or
    this recovery.

- [x] 2026-08-31 — **Config:** Two Claude Code profiles, and only two.
  - Result: A third configuration existed at `~/.claude/.claude.json` — one
    project, one MCP server, and its own `oauthAccount` binding
    `info@busirocket.com` to *Favish's* organization, crossing the
    email-separation rule in the global guidance. It is reached by setting
    `CLAUDE_CONFIG_DIR=~/.claude`, which looks like the way to name the
    personal profile and is not: Claude Code keeps its config at
    `$HOME/.claude.json` when the variable is unset and at
    `$CLAUDE_CONFIG_DIR/.claude.json` when it is set, so pointing it at
    `~/.claude` starts a fresh empty profile and every MCP server silently
    disappears. Parked at `~/.claude-retired/` rather than deleted, because it
    carries auth. The two real profiles are **busirocket**
    (`info@busirocket.com`, plain `claude`) and **favish**
    (`<work-account>`, `CLAUDE_CONFIG_DIR=~/.claude-second-profile`).
  - `~/.claude/rules/claude-profiles.md` rewritten to name both profiles, their
    accounts, how each is started and which file each uses; to forbid
    `CLAUDE_CONFIG_DIR=~/.claude` with the reason; to record that an MCP
    `command` must be an absolute path; and to mark `openseo` as a deliberate
    per-profile difference rather than drift, since it is a BusiRocket service.
  - `.zshrc` gained `claudeb` beside the existing `claudef`, so both profiles
    are named rather than one being "the default". It runs
    `env -u CLAUDE_CONFIG_DIR claude`: a shell that already ran `claudef`, or
    any nested agent session, would otherwise send a bare `claude` to the
    Favish profile without saying so. Nothing in the shell ever set
    `CLAUDE_CONFIG_DIR=~/.claude`, so the stray profile came from an ad-hoc
    invocation about a month earlier — plausibly an agent following the old
    rule text, which called `~/.claude` "canonical" without saying it is the
    canonical *shared tree*, not a profile.
  - Evidence: both profiles answer with their own account and connect Atrium
    over MCP after the removal; asked in each profile, both quote the new rule
    back. `.zshrc` needs a real pty to verify — it returns early for agent
    shells and again for an interactive shell with no TTY — and under one both
    functions resolve.

- [x] 2026-08-31 — **Cutover:** The last two things the retirement left open.
  - Result: The dotfiles guidance is committed (`ff7e3b4`), which required
    finishing a real in-progress merge between the two machines — resolved as a
    union of `autoMode.soft_deny` so no machine lost a confirmation prompt. And
    MemPalace's knowledge graph is exported to
    `~/p/brain/inbox/mempalace-knowledge-graph-export-2026-08-31.md`, split into
    151 judgement triples worth keeping (closed audit findings, blockers,
    partners, enforced rules) and 1,761 code-structure triples CodeGraph can
    re-derive. That was the only MemPalace content not reconstructible from the
    archive, so its 118 GB is now free to reclaim whenever the operator wants.
  - Also corrected a wrong finding from 2026-08-30: the `~/.claude` profile was
    reported as loading no stdio MCP server. It loads all of them. The test had
    used `CLAUDE_CONFIG_DIR=~/.claude`, which reads a third, near-empty
    `~/.claude/.claude.json` rather than `~/.claude.json`.
  - Evidence: `git -C ~/p/dotfiles log -1` shows a two-parent merge commit;
    `claude mcp get atrium` connects under both real profiles.

- [x] 2026-08-30 — **Cutover:** MemPalace retired; Atrium serves Claude and
  Codex.
  - Result: The blocker was never synthesis coverage — it was freshness.
    Nothing refreshed the canonical archive, so the index was frozen. The first
    automated refresh took the archive from 11,164 to **23,449 conversations**
    and the index from 553,083 to **616,365 records** (`codex` alone
    21,219 → 57,712). `atrium-refresh` now runs hourly and at session end under
    a real `flock`. Read side: `atrium recall` (project-scoped, ~1.2 s, no
    embedder) replaced the mempalace SessionStart hook, and an MCP server with
    a resident `Embedder` serves both clients — first search 20.7 s, next
    2.7 s. The dense lane is complete for the first time: 19,198 of 19,198.
  - Evidence: commits `d37ed44`..`243f299`; 77 tests pass, ruff clean; the
    Favish profile and Codex were each asked to quote back a real episode
    through the new path, and Claude answers NO to a mempalace tool; a full
    `atrium-refresh` logged `2609 conversations -> 0 synthesis records
    written, 2609 unchanged` / `nothing to embed`, which is the vector-cascade
    fix proven on the live index.

- [x] 2026-08-30 — **Bugs:** Nine defects found auditing the stalled synthesis
  and the new cutover code, four rounds with Codex as adversarial reviewer.
  - Result: The drip loop had produced nothing for 30 h behind three of them —
    a manifest dropping a whole producer population from the index (3,686
    episodes, 580 conversations), a quota probe reading the 5-hour window while
    the weekly one sat at 100%, and a dead loop nothing restarted. The rest
    came out of review: `write_conversation` destroyed every vector it touched
    on reconciliation; the synthesis registry claimed keys with
    `os.rename`, which replaces; `recent_episodes` matched a project prefix
    with `LIKE`, where `_` is a wildcard and 2,585 workspaces contain one;
    `project_workspace` returned the cwd instead of the project and matched
    nothing for `--project .`; and `verify_build_stamp` answered any
    operational fault with "delete it and re-ingest", which the session-start
    hook forwarded into an agent's context as an instruction.
  - Evidence: commits `d37ed44`, `28e2c7b`, `6c4de9c`, `3403b5d`, `38efc71`,
    `243f299`; each defect pinned by a test.

- [x] 2026-08-27 — **Backend:** First slice: ingest the canonical
  rocket-agents archive into a two-lane lexical index with a CLI
  (`ingest` / `search` / `--substring` / `status`).
  - Result: End-to-end ingest and retrieval over real exports; the `WAL` vs
    `wall...` defect of the old system is closed by test (word lane returns
    only the exact hit; fragment behavior isolated in the substring lane).
  - Evidence: commits `ae79234`..`5ff9cbb`; `uv run --with pytest pytest
    tests/ -q` — 19 passed; `ruff check` clean.

- [x] 2026-08-27 — **Bugs:** Two defects found self-reviewing the first slice
  against real data.
  - Result: Version/identifier queries no longer return nothing (`3.7.0`,
    `C#`, `GPT-5.3` become phrase queries), and the <120-char message filter
    was replaced by a confirmation-pattern filter — the old filter discarded
    43.4% of real messages (the 26.4% figure came from the old chunked index,
    a category error); the new one discards 1.0%.
  - Evidence: commit `2985c3a`; `tests/test_lexical_lanes.py` version test
    against a real index.

- [x] 2026-08-27 — **Bugs:** Codex adversarial review (BLOCK) — three
  criticals and three minors fixed.
  - Result: Record identity is now `sha256(conversation_id, event_id)`
    (canonical event IDs are only conversation-local; collisions lost rows and
    mixed provenance — OpenCode stored 2,569 of 2,586), re-ingest reconciles
    and deletes superseded records (corrected redactions now reach the index),
    ingest is atomic with trigger-maintained FTS, the substring lane is
    exposed via `--substring`, negative `--limit` is rejected, and read-only
    URIs escape `?`/`#` in paths.
  - Evidence: commit `83ac330`; re-ingest of the same OpenCode export stores
    2,586/2,586 with the 17 collisions preserved; 19 tests green. Review
    transcript: Codex rollout `01a04379` (2026-08-27).

- [x] 2026-08-27 — **Infrastructure:** Repository created and published:
  `BusiRocket/atrium`, private, 5 commits; README and `AGENTS.md` record the
  layer boundary and the measured decisions (embedder, fusion weights,
  separate lexical lanes, addressable dense lane).
  - Evidence: https://github.com/BusiRocket/atrium (visibility verified
    PRIVATE); `git log --oneline` 5 commits.

- [x] 2026-08-27 — **Pending Decisions:** Design converged after three
  adversarial Codex rounds with real measurements over the user's corpus.
  Settled: Atrium is layer 2 (derived, disposable) over the rocket-agents
  canonical archive and brain; CLI core with thin adapters; FTS5 over
  everything, vectors only over the semantic layer; `embeddinggemma-300m`
  (dense R@10 70.4% vs 40.8% for the English-only default on this corpus);
  fusion 70/30 (five-fold CV); synthesis promoted to the core.
  - Evidence: benchmark tables recorded in `AGENTS.md`; session `a88ac62e`
    (2026-08-26/27) and Codex rounds 1-3.

- [x] 2026-08-27 — **Retrieval:** Dense lane and adaptive hybrid retrieval
  built and verified against real data. Embedder: `embeddinggemma-300m` ONNX
  q8 on CPU, per-batch NaN/zero validation, L2-normalized; vectors only over
  `note`/`synthesis` roles; fusion weighted RRF 70/30 k=60; adaptive routing
  (dense-only when lexical is blind, lexical-only when nothing is embedded);
  lanes addressable via `--words`/`--dense`/`--substring`.
  - Result: 235 curated brain notes -> 3,599 chunks ingested and 3,599/3,599
    embedded; real hybrid search answers in ~1.6 s with `lane=fused`; batching
    by text length fixed an 8-minute stall (padded attention cost).
  - Evidence: commits `a2e3d0c`, `72295bb`, `8fbe4c3`; 38 tests green;
    `atrium search "WAL SIGBUS" --words` returns the exact 2026-08-25 SIGBUS
    conversation; `atrium search "3.7.0" --words` returns `3.7.0-prefetch`
    records with punctuation intact.

- [x] 2026-08-27 — **Self-improvement:** Studies directory created with the
  pending second research round: `docs/studies/mem0.md`, `letta-memgpt.md`,
  `graphiti.md` — mechanisms, what to steal mapped to the disposable-index
  constraints, what to avoid; researched via Codex with live web search,
  claims cited.
  - Evidence: commit `aa81f8a`.

- [x] 2026-08-27 — **Integrations:** Canonical archive materialized durably
  and the codex source landed. rocket-agents gained `--allow-partial`
  (fail-closed default; partial manifests declare `complete:false` + every
  skip), unblocking codex: 4,356 conversations -> 21,219 records ingested.
  The merged durable archive lives at
  `~/.local/share/rocket-agents/conversations/archive.jsonl` (11,164
  conversations, 1.5 GB, per-consult XDG decision), built via
  `conversations:import --apply` per source and verified by a convergence
  dry-run (added 0, duplicates 4,734). Index total: 538,430 records across 7
  sources.
  - Evidence: rocket-agents commits `bfa54ec`, `3f35a60` pushed; `atrium
    status`; import dry-run output.

- [x] 2026-08-27 — **Cross-project (mempalace):** Retirement calls executed
  per the two-agent consult: the `embeddinggemma` re-embed is skipped (`[-]`,
  36 h CPU on a retiring system), and the private-key-shaped drawers are
  purged — re-scan found 7 live matches (stricter body heuristic; the earlier
  14 predates the base64/checkpoint purges), daemon dry-run matched 7/7,
  delete removed 7/7, post-scan finds 0. No values printed. Raw-transcript
  mining deliberately stays on until Atrium replaces the live system.
  - Evidence: `mempalace_delete_drawers` dry-run and delete results;
    read-only re-scan count 0; `~/p/mempalace/TODO.md` updated.

- [x] 2026-08-27 — **Bugs:** Second adversarial Codex review (BLOCK, nine
  findings, all [REAL] and reproduced) closed the same day. Critical: absent
  conversations/notes were never swept on re-ingest, so upstream deletions and
  redactions never reached a long-lived index — fixed with a per-provider
  sweep (`--partial` opts out). High: pipeline version not bumped with an
  admission change; populated unstamped indexes silently adopted; mid-embed
  reconciliation could attach a stale vector to a new revision; the adjacency
  verifier dropped diacritic-folded hits and could be exhausted by a wall of
  false candidates; hybrid truncated lanes to the output limit before fusing.
  Medium: unbroken oversized paragraphs bypassed the chunk bound (a 17,999-char
  chunk embedded identically to its prefix); busy_timeout was set after
  journal_mode (43/100 concurrent first-opens failed); dense/fused score ties
  followed physical row order and diverged between machines.
  - Evidence: commit `71b8eb3`; 49 tests green; review transcript in Codex
    rollout `01a04450` (2026-08-27); index rebuilt under pipeline 2.

- [x] 2026-08-27 — **Integrations:** Every exportable source is in the index —
  including four that never reached the old system's memory (cursor, opencode,
  pi, openclaw). Totals: claude-code 442,447 records (4,734 conversations,
  566 MB export, 4m40s ingest), cursor 67,568 (2,002), opencode 2,586 (67),
  pi 63, openclaw 2, brain notes 3,599 = 516,265 records, 1.8+ GB index.
  Stored counts match the export CLI exactly at every size.
  - Evidence: `atrium status` per-provider table; export logs `ok: true` for
    all four new sources.

- [x] 2026-08-27 — **Bugs:** Adjacent-token phrase false positive closed
  (Codex review finding 6). `3.7.0` no longer matches `allocate 3 7 0 workers`:
  punctuated terms carry an adjacency verifier requiring parts joined by
  punctuation (underscore included) in the stored text; mixed queries keep OR
  semantics untouched.
  - Evidence: commit `103a065`; `tests/test_lexical_lanes.py` exclusion,
    snake_case and mixed-query tests (10 passed).

- [x] 2026-08-27 — **Backend:** `build_metadata` written and enforced (Codex
  review finding 5). New indexes are stamped with schema+pipeline versions;
  opening a mismatched or unstamped index fails with the remedy (delete and
  re-ingest); `status` reports the stamp.
  - Evidence: commit `132d776`; `tests/test_build_stamp.py` (4 tests);
    `atrium status` prints `built by: schema 2, pipeline 1`.

- [x] 2026-08-27 — **Backend:** Per-ingest O(corpus) FTS rebuild (Codex review
  finding 4) — verified already fixed by `83ac330` before this run: both FTS
  lanes are trigger-maintained, no rebuild call exists anywhere
  (`rg rebuild|optimize` returns only comments), and ingest is one
  transaction with per-conversation delete+insert.
  - Evidence: `atrium/store/schema.py` triggers; `tests/test_index_consistency.py`.

- [-] 2026-08-27 — **Ingest:** "Decide whether Trae `unknown`-role events are
  admissible" — resolved by looking at the data: the full Trae export holds 3
  events with texts `rule`, `code`, `folder` from `state.vscdb:ItemTable` —
  VS Code workspace metadata, not conversation. The admission gate is correct
  to drop them; the defect is the layer-1 exporter, filed in
  `~/p/rocket-agents/TODO.md`.

- [-] 2026-08-27 — **Refactors:** "Bounded semantic layer via admission gate
  on raw drawers" — superseded. Measured: a deterministic filter removes only
  27.5% of 1.34M drawers, leaving 972,760 vectors (1.49 GB brute-force per
  query). Replaced by: vectors only over synthesis + curated notes (~34k).

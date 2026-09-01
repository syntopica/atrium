# TODO Log

> Searchable record of closed project work. Active work lives in `TODO.md`.

## 2026

### 2026-09

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

- [x] 2026-09-01 — **Observability:** `atrium ingest` reports what it admitted
  per role and what each admission rule rejected, per kind and role.
  - Result: new `atrium/ingest/admission_tally.py`; `to_records` takes an
    optional tally and counts `kind <x>` / `role <x>` / `empty or
    acknowledgement` / `missing event id` rejections; ingest prints
    `admitted:` and `rejected:` lines ranked by count. The 162,225 tool-call
    records the mempalace recovery mis-filed would now be the first line of
    output.
  - Evidence: `tests/test_admission_breakdown.py` (3 tests); suite 105 passed.

- [x] 2026-09-01 — **Observability:** `atrium status` names every synthesis
  population and how many episodes of each the index serves.
  - Result: new `atrium/synthesize/population_report.py` and
    `choose_served_records.py` (chooser extracted from `_ingest_synthesis`,
    now shared, so status reports exactly what ingest would serve). Rows
    carry records/episodes/served, flag models missing from the active
    recipe, and mark a population serving zero episodes with
    `<- SERVES NOTHING`. On a machine without a registry status reports
    nothing and writes nothing (the manifest is created on first use, and a
    status must not write).
  - First live run: `claude-sonnet-5` (the 383-episode Max-lane tranche,
    4.7M input tokens) serves 0 episodes — fully shadowed by
    `codex-cli-default`, which covers every episode it has. Expected under
    the priority, but now visible instead of assumed. Status now costs ~7s
    (one registry pass, ~16k records).
  - Evidence: `tests/test_population_report.py` (4 tests); suite 109 passed.

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

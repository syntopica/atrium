# Alternatives verdict

## Verdict

**Do content-addressed immutable capture segments, with one deterministic set reducer and one disposable local SQLite state database. Do not implement the full `DESIGN.md` protocol now.**

One successful capture should publish one immutable segment containing only the changed conversation fragments. Its final name should contain a hash of its exact bytes. Synchronization should union missing segment files; materialization should union the fragments in every segment by content identity. A no-op capture should publish nothing. Keep the initial migrated corpus as one verified base segment and add small segments thereafter.

This is option F. It is the useful center of option C without its distributed-log control plane. It eliminates the measured publication rewrite and gives capture the smallest plausible incremental fast path:

- publication changes from a 4 GB read, full backup, and full rewrite to one write proportional to changed fragments;
- capture changes from reparsing every provider artifact to fingerprinting every path and fully parsing only changed artifacts. This is a phase-one hypothesis, not yet a claim that the full 226.91-second cost disappears: one changed monolithic SQLite database or large JSONL may still dominate.

At the observed maximum cadence, one segment per non-empty 20-minute capture is at most about 72 files per active writer per day or 26,300 per active writer per year. If all four installations independently captured at that cadence, the archive-wide ceiling would be about 288 per day or 105,200 per year; the actual count should be lower because no-op captures publish nothing and not every installation necessarily captures providers. That is still a better filesystem shape than option A's one file per conversation revision, while giving `rsync` immutable objects it can safely union. A fresh host copies the base segment and all later segments, validates their hashes, and rebuilds disposable state.

The strongest argument against this recommendation is deletion. A monotonic fragment union cannot honor a later redaction or intentional event removal: an older segment still contains the removed bytes. It also leaves full historical revisions in place and makes a cold rebuild grow with total history. If explicit archive deletion, legally required erasure, or bounded canonical retention is already a hard requirement, the observed-remove tombstones and snapshot machinery from option C become load-bearing. They are not load-bearing for the current scheduled path, which has no deletion producer and must never interpret a missing provider artifact as deletion. Event corrections are different: current event IDs exclude kind, role, and timestamp, so F must retain C's durable reviewed event-variant resolution entry in a segment. A lexical fallback alone would let an old normalizer keep winning over an operator's reviewed correction.

## What the source actually requires

The measured write amplification is real and directly explained by the current implementation. `importConversationExport.ts` loads the whole archive, takes another full backup, and writes the whole store again. `sync-conversations` runs full provider exports and exchanges full archives. Capture separately discovers every artifact and calls `captureConversationArtifact` for each one; `captureConversations.ts` starts with an empty map on every run. Fixing publication alone therefore leaves the larger 226.91-second capture pass intact.

The merge problem is also real. The current pairwise merge upgrades schema-v1 records, orders two inputs by provenance hash, unions events, and hashes the two provenance hashes. That is commutative for a pair, but the nested provenance calculation and two-input metadata selection are not an associative reducer over an arbitrary set of revisions. Every viable option needs one set reducer over distinct fragments. Storage format does not remove that requirement.

`DESIGN.md` is disproportionate to that irreducible core. Its current section 9 names 82 new Rocket Agents production files, 13 new Rocket Agents test files, 13 new Atrium modules, five new Atrium test files, and three explicitly new dotfiles: at least 116 named new files before fixtures, plus many changed files. That is not the brief's older estimate of roughly 45 TypeScript files. The current Rocket Agents conversation directory has 145 files, so the proposal would add more than half of the area's current file count in production files alone.

The newly committed schema-v2 upgrade helps the simpler design. `upgradeConversationRecord.ts` is a pure mapping from each old event ID to `sha256(conversation_id + NUL + old_event_id)`. The migration already must stream every record once, so it can upgrade and place the result directly into the new base segment. Atrium's current worktree already has an idempotent synthesis-registry re-key that preserves paid model output. Storage migration and synthesis re-key must be one coordinated cutover, but neither requires a frontier or snapshot protocol.

## Comparison

Implementation sizes below are engineering estimates under the repository's one-export-per-file rule. Option C is counted from the current `DESIGN.md`; the other ranges include production code, focused tests, and orchestration changes, but not unchanged reusable files.

| Option | Cost to add N conversations or revisions | Sync payload | Concurrent writers and the 353/356 case | Fresh-host seed | Protection of the 4,617 archive-only conversations | Approximate implementation size | Ongoing burden | What it forecloses relative to C |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. One content-addressed file per conversation revision | `Theta(sum of full changed record bytes)` and N atomic files; one derived-index transaction. The proposed path must include a revision hash, such as `objects/ab/<conversation-id>/<fragment-hash>.json`; `objects/ab/<conversation-id>.json` cannot retain divergent revisions. | Full filename/stat inventory plus only missing objects. `rsync --ignore-existing` is safe only after the receiver validates that the hash in every final name matches its bytes. | Different revision hashes coexist. A deterministic reducer unions F353 and F356; the result has all 356 events when F353 is a subset. A mutable conversation-id-only path loses one side. | Copy all objects, validate, rebuild the local index, and run a full Atrium ingest. | Migration writes one immutable object for every v1 record; scheduled capture never deletes an object because its source disappeared. Keep the v1 file and an independent verified backup. | About 25-35 files. | Low to medium. At 30,000 objects, sharded directories are ordinary; at 300,000, APFS and `rsync` metadata scans need measurement. Revision bodies accumulate. | No safe redaction/deletion until tombstones exist; no bounded history; metadata enumeration grows with object count. |
| B. Git repository of per-conversation files | N blobs, N tree entries, and usually one commit; later packing may delta-compress related JSON. The actual elapsed time, peak RSS, temporary disk, and rewritten bytes for a 4 GB repack are unknown until benchmarked on a copy of this corpus; that unknown is part of B's cost. | Git negotiation plus a pack containing missing commits, trees, and blobs. | Git merges non-overlapping immutable revision paths, but Git is not the semantic reducer. If both hosts edit one conversation path, Git reports a content conflict. Safe automation still requires revision-distinct paths and the same F353/F356 set reducer as A/F. | Clone or bundle/fetch the repository, verify the ref, then materialize and ingest. | Keep every migrated record reachable from a protected ref and retain an independent verified bundle/backup. Git history is not a substitute for off-machine durability. | About 25-40 files, including Git lifecycle and recovery tests. | Medium to high. Commit/ref policy, detached or divergent branches, automatic merge commits, GC, repack, fsck, and accidental remote publication become archive operations. Git's own documentation says GC repacks revisions and warns that aggressive repacking needs tailored benchmarks. | Safe pruning becomes history rewriting; same-path conflicts remain; the canonical archive becomes coupled to Git availability and repository hygiene. |
| C. `DESIGN.md` journal plus snapshots | One immutable batch containing N fragments, derived-index updates, and periodic full snapshot/compaction work. Normal work is proportional to changed bytes. | Missing batches in steady state; one full snapshot after compaction; inventories, heads, memberships, and acknowledgements. | Fully specified: distinct writer sequences, vector frontier, set reducer, observed-remove operations, and deterministic divergent-snapshot reconciliation. F353 and F356 both survive. | Transfer the current snapshot and every active post-frontier batch, bind a writer identity, enroll the peer, validate, and rebuild indexes. | The initial snapshot contains every record. Tombstones name observed fragment hashes and source absence cannot create one. Peer acknowledgements gate pruning. | At least 116 named new files: 82 Rocket Agents production, 13 Rocket Agents tests, 13 Atrium modules, five Atrium tests, and three new dotfiles, plus fixtures and changed files. | Very high. Two canonical serializers/reducers, five entry kinds, writer identity, sequence allocation, frontier logic, snapshot CAS, compaction, peer membership, acknowledgement retention, two derived indexes, and migration/recovery matrices must evolve together. | Almost nothing functionally; it forecloses a small, quickly auditable first implementation and creates the largest maintenance surface. |
| D. Canonical SQLite | Local add cost is excellent: insert immutable fragment/event rows in one WAL transaction, proportional to changed rows/pages. `VACUUM INTO` or the backup API creates a consistent copy but writes the database again. | Under the alternative as posed, transfer a consistent database copy, roughly the current database size, attach it locally, merge, then send a merged copy back. That is one or two corpus-sized transfers per pairwise cycle. Native Node SQLite also exposes sessions/changesets, so the categorical claim that SQLite can only do whole-file transport is too strong; durable incremental changesets would, however, reintroduce a log, peer progress, and conflict policy. | `INSERT ... ON CONFLICT` is safe only when the primary key is immutable fragment or event-variant identity. One row keyed only by conversation ID overwrites either F353 or F356. With fragment rows, `INSERT OR IGNORE ... SELECT` unions both and a reducer materializes 356 events. A writer during snapshotting remains for the next cycle. | Copy one consistent database snapshot, run integrity and semantic checks, then open normally. | Store every migrated v1 record as an immutable fragment row; never delete on source absence; retain verified database backups and v1. | About 20-30 files. | Medium. SQLite supplies transactions, WAL, integrity checks, backup, and queryable state, but canonical corruption has a whole-database blast radius and multi-host snapshot/merge is application policy. | Cheap missing-object sync under the `VACUUM INTO`/`ATTACH` design. Adding native changesets removes that limitation only by adding much of C's durable replication protocol. |
| E. One append-only JSONL file | One append proportional to N fragment lines. A process lock makes local appends atomic enough if each line is self-validating; a torn final line still needs recovery rules. | Raw `rsync` cannot union divergent tails. Either exchange whole journals, currently about 4 GB each, or add hash inventories and delta bundles. The latter is already a segmented-object protocol hidden behind a mutable file. | Local writers can serialize. Cross-host tails at the same offset diverge; neither append position nor timestamp decides authority. Semantic sync must exchange distinct fragment hashes and run the reducer for F353/F356. Compaction must freeze writers or use a replacement CAS. | Copy the whole journal, validate every entry, rebuild the hash/index state. | Put all migrated records in the initial journal and never infer deletion. Back up the journal independently. | About 20-30 files once tail recovery, hash index, semantic sync, and rare compaction tests are honest. | Medium to high. It looks tiny until the first divergent-tail sync, crash tail, or compaction; then it acquires most of a journal protocol while retaining one large mutable failure domain. | Direct missing-file transport, independently recoverable objects, safe online compaction, deletion, and bounded replay. |
| F. Content-addressed immutable capture segments — recommended | One atomic segment per non-empty capture: `Theta(sum of changed fragment bytes + one header/footer)`, independent of corpus size. One local SQLite transaction records object hashes, materialized conversations, capture fingerprints, and pending Atrium work. | Inventory plus only missing segment files. The 4 GB base segment is transferred once; normal sync transfers the new segment bytes. | Concurrent hosts create different content hashes, so both segments survive. The single Rocket Agents reducer unions every distinct fragment and applies durable reviewed event resolutions. No writer ID, sequence, frontier, or last-writer rule is needed. | Transfer and hash-validate the base and all later segments, rebuild the disposable SQLite state, emit a full materialized export, and ingest Atrium once. | The base segment contains all 30,721 migrated records, including the 4,617 with no source rollout. Source disappearance only evicts a capture-cache row; it never changes canonical segments. Keep v1 and a verified off-machine copy. | About 37-45 new or changed files; a category-level count appears below. | Low to medium. Immutable publication and hash validation are simple; one reducer and one disposable database are the main owned mechanisms. Segment count grows by capture transactions, not conversations. | No explicit deletion/redaction, no bounded historical storage, no peer-aware pruning, and cold rebuild cost grows with retained segment history. |

## Why F is simpler enough

F keeps these parts of `DESIGN.md`:

- the data/state namespace split;
- immutable final objects, temporary staging, exact hashes, atomic publication, file and directory sync, and refusal to replace a different object;
- full normalized fragments as canonical inputs;
- one commutative, associative, idempotent set reducer in Rocket Agents;
- retention and diagnostics for same-event-ID byte variants, a deterministic unresolved tie-break, and one durable reviewed-resolution operation that survives stale-normalizer segments;
- a disposable SQLite index that can be rebuilt from canonical segments;
- incremental source-artifact fingerprinting;
- source absence never creating deletion;
- staged, hash-verified, no-`--delete` synchronization;
- frozen-writer migration, retained v1 rollback data, per-ID/event semantic equivalence, and independent backups;
- the schema-v2 record upgrade and synthesis-registry re-key during the same cutover.

F deletes or defers these parts:

- `format.json`, mutable `current.json`, archive ID binding, durable writer identities, per-writer sequence numbers, `baseRevision`, and vector frontiers;
- snapshots, compare-and-swapped head replacement, compaction thresholds, divergent-snapshot joining, and peer-gated pruning;
- tombstone, peer-enrollment, and peer-retirement entry types and their command families;
- acknowledgement quorum, the 24-hour floor, the 30-day no-ack ceiling, route-to-peer identity state, and returning-retired-writer recovery;
- separate `archive-index.sqlite3` and `capture-index.sqlite3`; one disposable database can hold object, materialization, fingerprint, and pending-delivery tables;
- Atrium's snapshot cursor, per-writer cursors, fragment/event-origin tables, Python reducer, and 13 proposed new Python modules;
- JSONL prefix-chunk checkpoints, cached parser accumulators, and SQLite row cursors in the first release;
- every peer, deletion, compaction, and lock CLI that exists only to operate the deferred protocol; keep one migration command, one verifier, one inventory command, and one event-resolution command.

Atrium does not need to implement the reducer. Rocket Agents can emit a small ordinary export slice containing only newly materialized or changed conversation IDs, and the existing `atrium ingest --partial` path already writes those conversations without sweeping absent IDs. A pending-delivery table in disposable Rocket Agents state makes a crash before Atrium ingestion retryable; deletion of that state forces a full materialized rebuild. This keeps canonical policy in Rocket Agents and lets Atrium remain disposable.

The 37-45-file estimate for F is intentionally auditable at category level under the one-export-per-file rule: 3-4 segment/resolution schemas; 7-9 publication, validation, inventory, and reducer units; 3-4 state-store/fingerprint/incremental-capture units; 3 migration/semantic-verification units; 8 command/entrypoint files for capture, migrate, verify, inventory, and resolution with some commands sharing an entrypoint where the current CLI convention permits; 6-8 focused tests; 4-6 changes to current capture/import/package files; and 3 dotfiles sync/refresh/test changes. It proposes no new Atrium module because `ingest --partial` already exists. A file-by-file implementation plan should pin the exact number before coding, but this range and C's 116-file count now include equivalent categories.

## The merge answer

Let host A capture fragment F353 and host B capture fragment F356 for the same conversation. Their complete canonical record bytes differ, so their fragment hashes differ. Each host publishes its fragment in an independently hashed segment. Synchronization transfers both missing segments and never overwrites either.

The reducer then:

1. upgrades every fragment to schema 2 before identity comparison;
2. deduplicates exact fragment hashes;
3. validates common conversation ID, source, and source ID;
4. unions events by event ID;
5. retains every canonical byte variant when one event ID has different bytes, emits a diagnostic, and selects a deterministic byte-order fallback only while unresolved;
6. applies a content-addressed reviewed-resolution entry when present, including observed variant hashes and superseded resolution hashes, so a stale normalizer cannot displace the reviewed choice;
7. sorts materialized events deterministically and derives metadata and provenance from the entire sorted fragment set.

If F353 is a prefix/subset of F356, the materialized record has 356 events. If each side has unique events, it has their union. Neither fragment supersedes the other. Processing F353 then F356, F356 then F353, or duplicates of either produces identical bytes. Host, arrival order, timestamp, file mtime, and segment order are never authority.

This reducer is mandatory for A, B, D, E, and F. Option C specifies it correctly; the mistake is treating every surrounding distributed-systems mechanism as equally mandatory.

## Minimum viable incremental capture

The first incremental capture should be deliberately boring:

1. Enumerate the configured roots as today. Metadata discovery remains O(path count).
2. In one disposable SQLite database, key artifact rows by source, relative path, and storage kind. Store device, inode, size, nanosecond mtime/ctime, adapter/normalizer/redactor versions, and the fragment hashes produced by the last successful capture.
3. Open with `O_NOFOLLOW` and compare `fstat` before and after reading. For provider SQLite, include main, WAL, and SHM fingerprints and read a consistent source view.
4. If metadata and versions are unchanged and every cached fragment is present in the rebuilt object index, do not read the payload.
5. If changed, parse and normalize that entire artifact using the existing adapter. Do not revisit other payloads.
6. Publish the segment first. Only after the segment and materialized state are durable should the cache row advance. A crash before that point causes a harmless recapture.
7. Cache loss, schema mismatch, or normalizer change triggers a complete pass. That is a recovery cost, not the normal path.

Do not assume JSONL prefix-chunk checkpointing can be dropped permanently. It still rereads the prefix to prove its chunks, requires a durable representation of parser/normalizer accumulator state, and multiplies corruption and versioning cases, so the first experiment should omit it. But the measurements supplied do not attribute the 226.91 seconds by artifact. A changed OpenCode database currently joins and scans all sessions/messages/parts, Cursor scans its matching key ranges, and a changed large JSONL restarts at byte zero. Instrument per-artifact elapsed time, bytes read, and records emitted before and after the simple cache. Run warm no-op plus one-changed-artifact cases for every storage kind. Accept the simple phase only if the live-scale p50 one-change run is no more than 10% of the 226.91-second baseline and no single changed artifact dominates it. Otherwise, JSONL suffix resume and/or a proven monotonic provider row cursor remains in the first releasable implementation for the offending source.

## Migration

The schema-v2 change makes this the correct moment to change shape:

1. Install the migration-capable code on every archive-holding host, freeze capture/sync/SessionEnd writers, and inventory every distinct archive holder. An unreachable known holder blocks lossless cutover.
2. Converge v1 archives while frozen. Preserve the original archive and a verified off-machine copy. Record byte size, file hash, manifest count, manifest content hash, and a sorted semantic inventory.
3. Stream v1 once. Apply `upgradeConversationRecord` to every record and write one immutable base segment through the same canonical serializer and validator used in steady state. Do not recapture providers; that would omit the 4,617 archive-only conversations.
4. Compare old and new inventories with the exact v1-to-v2 event-ID mapping. Require equal conversation IDs, event counts, event text/kind/role/timestamps, metadata, and original provenance. Record-hash equality is not required across a deliberate schema change.
5. Snapshot and dry-run the 16,148-record synthesis registry, run its idempotent re-key, verify counts and collision report, and retain the pre-re-key copy until cutover acceptance.
6. Delete only a copy of disposable state, rebuild the Rocket Agents materialization from segments, emit a full materialized export, and rebuild a test Atrium index. Compare provider, conversation, record, FTS, synthesis, and vector inventories.
7. Seed each frozen peer by missing-segment transfer, verify identical segment-set digest and identical materialized-state digest, then run two no-op sync/dry cycles.
8. Unfreeze one trigger at a time, run one incremental capture and Atrium partial ingest, sync all peers, and require an immediate no-op dry cycle.
9. Keep v1 read-only through a recovery drill. Before unfreezing, rollback is code plus pointer/config rollback. After new segments exist, rollback must first export the current materialized state to a new validated v1 file so post-cutover conversations are not lost.

## Re-costing the three attractive alternatives

### Git at 4 GB

B's repack cost is unknown, not free and not safely inferable from the archive size alone. Benchmark a disposable 4 GB corpus-shaped repository with `/usr/bin/time -l git gc`, recording elapsed time, maximum RSS, free space before/after, loose-object count, pack bytes, and temporary peak bytes. Repeat after a representative day of revisions. Until that exists, the honest cost is “unknown corpus-scale maintenance.” Git documents that [`git gc`](https://git-scm.com/docs/git-gc) compresses revisions through repacking and that aggressive repacking costs substantially more time and needs a tailored benchmark. That uncertainty, plus semantic merge still living outside Git, is why B is not the default.

### Per-conversation files

A is viable after correcting its name to include a revision hash and adding the same set reducer. At the current 30,721 records, two-level sharding is reasonable; 300,000 files are not automatically an APFS failure. The real cost is repeated metadata enumeration over SSH, backup tooling behavior, and full-body duplication for every revision. Those should be benchmarked rather than assumed fatal. F is preferable because it reduces object count by grouping one capture transaction without adding a mutable shared tail.

### Canonical SQLite

`DESIGN.md` rejects SQLite too categorically. SQLite's [WAL documentation](https://www.sqlite.org/wal.html) establishes cheap append-oriented commits and concurrent readers; [`VACUUM INTO`](https://www.sqlite.org/lang_vacuum.html#vacuuminto) gives a consistent compact copy; [Node's native SQLite API](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html) also exposes backup and session/changeset operations. SQLite is a credible canonical local store.

The rejection remains correct only for the proposed multi-host transport. Copying a live or vacuumed database and attaching it means corpus-sized transfer. A changeset-based transport can be incremental, but it then needs durable changeset retention, peer progress, replay idempotence, and semantic conflict handling. That is a journal protocol under a SQLite API. D is therefore the best fallback if operational simplicity is valued above network/disk volume, but it is not better than F for four intermittently connected installations.

## Verification

Run from this directory:

```bash
test -s ALTERNATIVES-VERDICT.md && \
grep -Fq 'Do content-addressed immutable capture segments' ALTERNATIVES-VERDICT.md && \
for option in 'A. One content-addressed file' 'B. Git repository' 'C. `DESIGN.md`' \
  'D. Canonical SQLite' 'E. One append-only JSONL' \
  'F. Content-addressed immutable capture segments'; do \
  grep -Fq "$option" ALTERNATIVES-VERDICT.md || exit 1; \
done && \
for subject in 'The merge answer' 'Minimum viable incremental capture' 'Migration' \
  'F keeps these parts' 'F deletes or defers these parts' '4,617' 'F353' 'F356' \
  'strongest argument against'; do \
  grep -Fiq "$subject" ALTERNATIVES-VERDICT.md || exit 1; \
done && \
test "$(( $(grep -c '^```' ALTERNATIVES-VERDICT.md) % 2 ))" -eq 0 && \
! grep -Eq 'TODO|TBD|PLACEHOLDER' ALTERNATIVES-VERDICT.md
```

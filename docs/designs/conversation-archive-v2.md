# Canonical conversation archive v2 — agreed specification

Design snapshot: 2026-08-31. Produced with codex over three review rounds and
kept here because the archive spans all three layers: `rocket-agents` owns and
implements it, Atrium ingests it, and the dotfiles transport moves it. Atrium
does not own this format; this copy exists so the reasoning survives, and
`~/p/rocket-agents` remains the place it is implemented.

Measured before anything was designed, on the live machine:

| term                                    | cost                                          |
| --------------------------------------- | --------------------------------------------- |
| v1 import adding one conversation        | 132.36 s, ~10.3 GB of archive I/O             |
| v1 full capture/export                   | 226.91 s, 2.78 GB written, 1.63 GB peak RSS   |
| refresh cadence actually observed        | every ~20 min, 4.5-8.4 min each               |
| archive at the time                      | 3,423,794,309 bytes, 27,041 conversations     |

Capture costs more than publication, which is why the specification covers
incremental capture (section 4.3) and not only the append path.

The three review rounds and what each changed are recorded in section 11; the
open risks the design does not close are in "Round 3: closure status".

---

# Canonical conversation archive v2

## Status and scope

This document specifies the canonical archive owned by Rocket Agents, the disposable index built by Atrium, the multi-installation transport, and the v1-to-v2 migration. It is an implementation contract, not code.

The goal is that steady-state capture and publication of `N` changed conversation fragments reads expensive payload data, writes, and indexes data proportional to those changed artifacts. Full-corpus work is permitted only for initial migration, explicit verification, capture-cache or normalizer-version recovery, corruption recovery, and threshold-triggered compaction. Metadata discovery is measured separately.

The design preserves these existing properties:

- Rocket Agents is the only owner of canonical conversation data.
- Atrium can be deleted and rebuilt entirely from Rocket Agents data.
- An import that started from a stale local archive revision refuses publication.
- Conversation revisions merge as a commutative, associative, idempotent union of events; arrival order and host do not choose a winner.
- Durable archive data remains under `~/.local/share`; locks, transfer staging, cursors, acknowledgements, and derived indexes remain under `~/.local/state` or Atrium's disposable index.
- No dependency is added to Rocket Agents.

The main correction to the earlier recommendation is that the derived Rocket Agents index cannot be `id -> latest revision`. There is no authoritative latest revision. It must retain the active fragment set, tombstoned fragment set, event origins, and materialized record hash for each conversation. The other correction is that the journal is physically segmented by append transaction, not one mutable file. It is not partitioned by source or time.

The source read also establishes that append-only publication is only half of the cost problem. `captureConversations.ts` creates a new in-memory map, `captureConversationArtifacts.ts` visits every discovered artifact, and `captureConversationArtifact.ts` reparses and re-redacts each artifact. Neither capture path has a cache. V2 therefore includes incremental source capture as part of the required design, not as a later optimization.

## 1. Terms and invariants

**Fragment** means one complete normalized `ConversationRecord` observed from one source artifact or received from another archive. Its identity is its canonical byte hash, not its timestamp or arrival position.

**Batch** means one atomic append transaction containing one or more fragment, tombstone, event-variant-resolution, peer-enrollment, or peer-retirement entries. A batch is an immutable JSONL file.

**Snapshot** means a deterministic, immutable JSONL checkpoint containing the normalized CRDT state for every live or tombstoned conversation covered by a vector frontier.

**Frontier** means a sorted mapping from writer ID to the greatest contiguous batch sequence included in a snapshot.

**Head** means `current.json` plus every complete batch beyond its frontier. The head is the logical journal revision a reader observes.

**Archive peer** means one installation that has validated this archive ID, owns a distinct durable writer ID, and has self-enrolled that `(archiveId, writerId)` in the journal. SSH aliases, DNS names, and configured sync targets are routes, not peer identities. A target that has never held the archive is not a peer.

The following are hard invariants:

1. A final-named object is immutable. Existing final files are never overwritten.
2. Only footer-valid, filename-valid batch and snapshot files participate in a head.
3. A writer ID never publishes two different hashes at one sequence. Seeing that condition is corruption and stops all publication and ingestion.
4. Within one writer ID, final batches are contiguous. A candidate sequence is derived from the base head, but it becomes allocated only when the complete file receives its final name under the archive publication lock. A failed temporary write consumes no sequence.
5. A tombstone removes only the fragment hashes it names. It does not use wall-clock time and does not remove an unseen concurrent fragment.
6. Materialization is a set operation. It never folds records using arrival order.
7. The legacy `archive.jsonl` is not modified or deleted during migration.

## 2. On-disk layout

### 2.1 Durable data

All paths below are relative to `~/.local/share/rocket-agents/conversations/`:

```text
archive.jsonl                                  # immutable v1 migration source and rollback copy
local-writer.json                              # durable installation identity; never transported
archive-v2/
  format.json                                  # immutable archive identity and format declaration
  current.json                                 # atomically replaced snapshot reference
  journal/
    b_<writer>_<sequence>_<batch-sha256>.jsonl # immutable committed append batches
  snapshots/
    s_<snapshot-payload-sha256>.jsonl           # immutable compaction snapshots
```

`<writer>` is 32 lowercase hexadecimal characters. `<sequence>` is a 20-digit, zero-padded positive decimal integer. SHA-256 values are 64 lowercase hexadecimal characters. Directories are mode `0700`; all files are mode `0600`.

There are no source, provider, month, or year subdirectories. A journal segment exists only because one publication transaction must be atomic and independently transferable.

### 2.2 Ephemeral and derived state

All Rocket Agents state paths are relative to `~/.local/state/rocket-agents/conversations/`:

```text
archive.lock                    # short publication/compaction critical-section lock
sync.lock                       # one local transport at a time
archive-index.sqlite3           # disposable Rocket Agents materialization/index cache
capture-index.sqlite3           # disposable source-artifact fingerprints and parser checkpoints
transfers/<run-id>/             # incoming .part files and inventories
peer-acks/<archive>_<writer>.json # identity-keyed pruning acknowledgement; safe to lose
retention.json                 # disposable local first-seen times for the pruning floor
migration.freeze                # scheduler/hook freeze sentinel
migration/                      # reports and pre/post verification digests
```

Atrium continues to use `~/.atrium/index.sqlite3`. Its archive cursors are tables in that disposable database, not files in the canonical archive.

`local-writer.json` is durable coordination data, not disposable state and not a sync object. It contains `kind`, schema version, writer ID, creation timestamp, and—once v2 is seeded—the bound archive ID; it is mode `0600` and is included in the host's normal backup of `~/.local/share`. Migration preflight creates a distinct unbound writer identity on each v1 archive-holding installation with exclusive creation, which lets cable/Wi-Fi routes be grouped before v2 exists. Binding that identity to one archive ID is a single atomic transition; rebinding refuses. If a non-empty v2 archive has no readable bound identity, publication stops and asks the operator to restore it or run an explicit `conversations:writer-init --rotate-from <old-writer-id>` recovery; it never silently invents a new identity. Sync refuses if two active peer installations present the same writer ID. Multiple routes that return the same `(archiveId, writerId)` are aliases for one peer and produce one acknowledgement.

V2 never removes a writer from `coveredThrough`. A retired installation's final sequence remains a small permanent causal barrier so stale batches cannot reappear as active. Identity rotation is therefore rare and explicit; frontier growth is proportional to actual rotations, not refreshes. Peer retirement is an observed-remove journal operation specified in section 2.10; it changes acknowledgement membership, not the causal frontier.

### 2.3 Canonical JSON and hashing

Every object is UTF-8 without a BOM, serialized on one line with no insignificant whitespace, followed by one LF byte (`0x0a`). CRLF and a missing terminal LF are invalid. Integers are base-10 and the schemas contain no floating-point values.

Each schema has a fixed field order shown by the examples below. Optional fields are omitted, not emitted as `null`. `ConversationRecord`, `ConversationEvent`, and `provenance` use their existing TypeScript interface order. Arrays whose order is declared “sorted” use ascending Unicode code-point order; all identifiers and schema keys are ASCII. Both Node and Python implementations use shared byte fixtures to prove identical serialization.

`fragmentSha256` is SHA-256 over the canonical `ConversationRecord` bytes without a trailing LF. A batch checksum is SHA-256 over the exact header and entry line bytes, including the LF after every hashed line and excluding the footer. A snapshot payload checksum is defined the same way over its header and state lines. `snapshotStateSha256` is SHA-256 over the canonical materialized live `ConversationRecord` line for each live conversation, sorted by conversation ID, including each LF. It is the v2 materialized-state digest; because v2 provenance semantics differ, it is not expected to equal the v1 manifest hash.

### 2.4 `format.json`

This file is written once with `wx`, fsynced, and never replaced.

```json
{"kind":"rocket-agents-conversation-archive","schemaVersion":2,"archiveId":"7b8d1f826e9f7f9b2a1f405f499e76c7d0e70ef9360fc67ea0cb2da02fe89f38","createdFrom":{"kind":"rocket-agents-conversation-export","schemaVersion":1,"contentSha256":"a6cc84c39c9ff06dab00ebfabb846a89aedcb26219f3a2fec3d856391ed8f84d"}}
```

Fields:

- `kind`: literal shown above.
- `schemaVersion`: integer `2`.
- `archiveId`: `SHA-256("rocket-agents-conversation-archive-v2\n" + initialSnapshotStateSha256 + "\n")`. It is deterministic for identical migrations.
- `createdFrom`: optional migration provenance. For v1 it records the v1 kind, schema, and complete manifest hash.

### 2.5 `current.json`

`current.json` is the only mutable durable file. Its canonical bytes are:

```json
{"kind":"rocket-agents-conversation-head","schemaVersion":2,"archiveId":"7b8d1f826e9f7f9b2a1f405f499e76c7d0e70ef9360fc67ea0cb2da02fe89f38","snapshotFile":"s_4b21f4c9f37f8a4c7d20a570ef96be5d60ce1c9cf4b39d8869bc818181818181.jsonl","snapshotPayloadSha256":"4b21f4c9f37f8a4c7d20a570ef96be5d60ce1c9cf4b39d8869bc818181818181","snapshotStateSha256":"a6cc84c3f37f8a4c7d20a570ef96be5d60ce1c9cf4b39d8869bc828282828282","coveredThrough":[{"writerId":"0123456789abcdef0123456789abcdef","sequence":42}]}
```

Fields:

- `kind`, `schemaVersion`, `archiveId`: identify and bind the reference.
- `snapshotFile`: basename only; path separators are forbidden.
- `snapshotPayloadSha256`: must match both the filename and validated snapshot footer.
- `snapshotStateSha256`: must match the snapshot footer.
- `coveredThrough`: sorted by `writerId`; each sequence is the greatest contiguous sequence from that writer incorporated into the snapshot. Missing writers mean sequence zero.

The file contains no timestamp or local generation number, so any installations choosing the same snapshot produce identical bytes.

### 2.6 Batch header

The first line of every batch is:

```json
{"kind":"conversation-batch-header","schemaVersion":2,"archiveId":"7b8d1f826e9f7f9b2a1f405f499e76c7d0e70ef9360fc67ea0cb2da02fe89f38","writerId":"0123456789abcdef0123456789abcdef","sequence":43,"baseRevision":"66f81c4d4afb57858b9f6fd78d3b17d5c01f031876c4fe5f3f15edfe4f7b6a20","createdAt":"2026-08-31T18:00:00.000Z","entryCount":1}
```

Fields:

- `writerId`: stable installation ID from durable, host-local `local-writer.json`. Missing identity on a non-empty archive is a hard publication error, not automatic rotation.
- `sequence`: previous local sequence plus one from the recorded base head. It is confirmed and allocated inside the publication lock.
- `baseRevision`: exact archive revision observed before the batch was prepared.
- `createdAt`: informational UTC timestamp only. It never orders or resolves data.
- `entryCount`: exact number of following entry lines before the footer.

### 2.7 Fragment entry

```json
{"kind":"conversation-fragment","schemaVersion":2,"conversationId":"conv-1","fragmentSha256":"df329f33409eddf1e25ca34c0e7a78e15d7b69f7d69ddf7220e80b9f01010101","record":{"schemaVersion":1,"id":"conv-1","source":"codex","sourceId":"01abc","title":"Archive design","events":[{"id":"event-1","kind":"message","role":"user","text":"Preserve this","timestamp":"2026-08-31T17:59:00.000Z"}],"provenance":{"contentSha256":"source-hash","relativePath":"sessions/example.jsonl","redactions":0},"startedAt":"2026-08-31T17:59:00.000Z","updatedAt":"2026-08-31T17:59:00.000Z","workspace":"/Users/example/p/rocket-agents"}}
```

Fields:

- `conversationId`: duplicates `record.id` to allow bounded routing before parsing a large record; disagreement is invalid.
- `fragmentSha256`: canonical hash defined above; mismatch is invalid.
- `record`: the complete existing schema-v1 `ConversationRecord`. V2 changes the archive container, not the normalized provider record schema.

An already-active or already-tombstoned fragment hash is idempotent. A fragment with the same conversation ID but a different `source` or `sourceId` is invalid. Different canonical event bytes under one event ID are retained as event variants and reported as a conversation-scoped conflict; they do not invalidate the batch or stop unrelated publication and ingestion. With no active operator resolution, the materialized record uses the lexicographically lowest canonical event bytes for that ID. Section 2.9 defines the durable, order-independent override for a reviewed choice.

### 2.8 Tombstone entry

```json
{"kind":"conversation-tombstone","schemaVersion":2,"conversationId":"conv-1","removedFragmentSha256":["df329f33409eddf1e25ca34c0e7a78e15d7b69f7d69ddf7220e80b9f01010101"],"reason":"explicit-delete"}
```

Fields:

- `conversationId`: target conversation.
- `removedFragmentSha256`: non-empty, sorted, duplicate-free set of fragment hashes visible to the deleter.
- `reason`: one of `explicit-delete`, `source-redaction`, `migration-repair`, or `event-conflict-resolution`.

The operation is observed-remove. A fragment appended concurrently on the other host and absent from this array survives. This prevents a delete based on a stale host from silently destroying unseen events. A later explicit delete after convergence can remove the surviving fragment.

Tombstones are never inferred from a provider export, a missing path, a capture-cache eviction, or Atrium's absent-conversation sweep. That rule protects the 4,617 conversations whose provider artifacts no longer exist. Only Rocket Agents can emit them, through these explicit paths:

- `conversations:tombstone --conversation <id> --reason explicit-delete --apply` previews the active fragment hashes and resulting record/event removals, then appends a tombstone only with `--apply`.
- `conversations:redact --conversation <id> --replacement <validated-export> --apply` appends the fully redacted replacement fragment and tombstones the exact superseded fragments in the same batch. The reason is `source-redaction`; a source file merely disappearing or changing never invokes it.
- `conversations:repair --plan <reviewed-json> --apply` may use `migration-repair`, but only for explicit IDs and fragment hashes in a generated plan whose before/after semantic inventory is shown to the operator.
- `conversations:resolve-event-conflict` appends the durable resolution in section 2.9 after preview and `--apply`. It may additionally append a replacement fragment and tombstone obsolete fragments when the coverage rule in section 4.1 succeeds, but fragment cleanup is not the authority for the chosen variant.

The scheduled capture path has no tombstone capability. Atrium consumes tombstones but never creates them.

### 2.9 Event-variant resolution entry

An operator choice is a first-class journal operation, not an incidental consequence of deleting fragments:

```json
{"kind":"conversation-event-variant-resolution","schemaVersion":2,"conversationId":"conv-1","eventId":"event-1","chosenEventSha256":"65d7752c66a3cb85f55e0cbd7fd837f079a34afbf9f21088c3feea7a02020202","observedEventSha256":["65d7752c66a3cb85f55e0cbd7fd837f079a34afbf9f21088c3feea7a02020202","f40c18bd92d63a8d833bab78138d4cb1700f222fdcad09040404040404040404"],"supersededResolutionSha256":[],"reason":"normalizer-fix"}
```

Fields:

- `conversationId` and `eventId`: the exact conflict selected by the operator.
- `chosenEventSha256`: one event variant present in the base revision. The command refuses a missing choice.
- `observedEventSha256`: the sorted, duplicate-free complete variant set shown in the preview. It records the scope of review; a later unseen variant raises a new diagnostic but does not silently displace the chosen variant.
- `supersededResolutionSha256`: sorted hashes of active resolution entries the operator explicitly replaces. The resolution hash is SHA-256 of the canonical entry bytes without LF.
- `reason`: currently the literal `normalizer-fix` or `manual-correction`.

Active resolutions are all resolution entries whose hashes are absent from the union of `supersededResolutionSha256`. If exactly one chosen hash is named by the active set and that variant has an active fragment origin, it is canonical regardless of any later stale fragment carrying an older variant. If concurrent active resolutions choose different hashes, materialization uses the choice from the lexicographically lowest canonical resolution bytes to remain available, reports an `event-resolution-conflict`, and requires a new entry that observes and supersedes all competing resolution hashes. If the chosen variant loses every active origin, the resolution becomes dangling: materialization falls back to the unresolved byte tie-break and reports it. Resolutions and their supersession barriers survive compaction.

`conversations:resolve-event-conflict --conversation conv-1 --event event-1 --choose-event-sha256 <hash> --base-revision <revision> --apply` prints every canonical event body and a field-level diff of `kind`, `role`, `text`, and `timestamp`, plus fragment origins and normalizer versions. It refuses if the base revision or observed variant set moved. Fragment replacement/tombstoning is an optional storage cleanup after the resolution is durable; it is not required for correctness.

### 2.10 Peer enrollment and retirement entries

A target becomes a peer only by publishing this self-enrollment from a batch whose header has the same writer ID:

```json
{"kind":"archive-peer-enrollment","schemaVersion":2,"archiveId":"7b8d1f826e9f7f9b2a1f405f499e76c7d0e70ef9360fc67ea0cb2da02fe89f38","peerWriterId":"fedcba9876543210fedcba9876543210"}
```

The entry hash is its enrollment identity. The target must already possess and validate the archive head and its distinct `local-writer.json`; a reachable SSH target with no archive cannot enroll and never enters the acknowledgement set. A second SSH alias returning the same archive and writer IDs is only another route to this enrollment.

Retirement is explicit observed-remove membership:

```json
{"kind":"archive-peer-retirement","schemaVersion":2,"peerWriterId":"fedcba9876543210fedcba9876543210","removedEnrollmentSha256":["7f0c4d7a3b31c48d824128bc8d8ea449b777822ad9d209050505050505050505"],"reason":"operator-forget"}
```

`conversations:forget-peer --peer-id <writer-id> --apply` previews the last acknowledgement, unacknowledged frontier, retained objects, and the rule for a returning installation, then removes only the enrollment hashes shown. It never removes that writer from `coveredThrough`. A retired installation is refused by normal sync. To return, its unmerged objects are first imported into quarantine and reconciled explicitly; it then receives the full current snapshot, rotates to a new writer ID, and self-enrolls. This prevents an old installation from silently reviving a retired membership or stale variant.

### 2.11 Batch footer

```json
{"kind":"conversation-batch-footer","schemaVersion":2,"entryCount":1,"payloadBytes":922,"batchSha256":"e4e0f1a67d3f68d863f70f59eab2ae9d02126570c46dc4040404040404040404"}
```

Fields:

- `entryCount`: must equal the header and observed entry count.
- `payloadBytes`: byte count from byte zero through the LF after the final entry.
- `batchSha256`: checksum of those bytes and the hash component of the filename.

No bytes may follow the footer LF.

### 2.12 Snapshot header

```json
{"kind":"conversation-snapshot-header","schemaVersion":2,"archiveId":"7b8d1f826e9f7f9b2a1f405f499e76c7d0e70ef9360fc67ea0cb2da02fe89f38","coveredThrough":[{"writerId":"0123456789abcdef0123456789abcdef","sequence":43}],"peerMembership":[{"peerWriterId":"0123456789abcdef0123456789abcdef","enrollmentSha256":"7f0c4d7a3b31c48d824128bc8d8ea449b777822ad9d209050505050505050505","retired":false}],"liveConversations":1,"tombstonedConversations":0}
```

The frontier is sorted and contiguous. `peerMembership` is the materialized observed-remove enrollment set, sorted by writer ID; retired entries remain as barriers with `retired:true`. Counts describe the following conversation-state lines.

### 2.13 Live snapshot state

A live conversation is stored in normalized form so compaction removes repeated event bodies without losing fragment lineage needed for commutative replay and tombstones:

```json
{"kind":"conversation-live-state","schemaVersion":2,"conversationId":"conv-1","source":"codex","sourceId":"01abc","fragments":[{"fragmentSha256":"df329f33409eddf1e25ca34c0e7a78e15d7b69f7d69ddf7220e80b9f01010101","title":"Archive design","events":[{"eventId":"event-1","eventSha256":"65d7752c66a3cb85f55e0cbd7fd837f079a34afbf9f21088c3feea7a02020202"}],"provenance":{"contentSha256":"source-hash","relativePath":"sessions/example.jsonl","redactions":0},"startedAt":"2026-08-31T17:59:00.000Z","updatedAt":"2026-08-31T17:59:00.000Z","workspace":"/Users/example/p/rocket-agents"}],"eventVariants":[{"eventId":"event-1","eventSha256":"65d7752c66a3cb85f55e0cbd7fd837f079a34afbf9f21088c3feea7a02020202","fragmentSha256":["df329f33409eddf1e25ca34c0e7a78e15d7b69f7d69ddf7220e80b9f01010101"],"event":{"id":"event-1","kind":"message","role":"user","text":"Preserve this","timestamp":"2026-08-31T17:59:00.000Z"}}],"eventVariantResolutions":[],"supersededEventVariantResolutionSha256":[],"removedFragmentSha256":[]}
```

Fields:

- `source`, `sourceId`: common immutable identity.
- `fragments`: active fragment descriptors sorted by fragment hash. Each descriptor references sorted `(eventId, eventSha256)` pairs, preserving origin membership and permitting exact subtraction by tombstone.
- `eventVariants`: canonical event bodies stored once per distinct event hash, sorted by `(eventId, canonical event bytes)`, with the sorted fragment hashes that contain each variant. Most event IDs have one variant. Multiple variants retain a normalizer disagreement without duplicating bodies per fragment.
- `eventVariantResolutions`: active and superseded resolution bodies from section 2.9, each with its derived resolution hash, sorted by `(eventId, resolutionSha256)`.
- `supersededEventVariantResolutionSha256`: sorted permanent barriers so a stale snapshot or batch cannot reactivate an older operator decision.
- `removedFragmentSha256`: sorted observed-remove barrier, retained to prevent a stale peer from resurrecting removed history.

The snapshot does not inline a materialized `record`: that would duplicate every event body in the only corpus-sized object transferred after compaction. Rocket Agents materializes each line once while rebuilding its disposable index; Atrium does the same during a full snapshot reconciliation. Normal incremental reads use those caches. The extra O(events) CPU is paid only on snapshot build/rebuild and is already required to validate origin membership and `snapshotStateSha256`.

### 2.14 Tombstoned snapshot state

When no active fragment remains, removed content is omitted but the anti-resurrection barrier remains:

```json
{"kind":"conversation-tombstoned-state","schemaVersion":2,"conversationId":"conv-1","source":"codex","sourceId":"01abc","eventVariantResolutions":[],"supersededEventVariantResolutionSha256":[],"removedFragmentSha256":["df329f33409eddf1e25ca34c0e7a78e15d7b69f7d69ddf7220e80b9f01010101"]}
```

This is metadata, not a live record, and is excluded from `snapshotStateSha256` and Atrium records. Resolution bodies and supersession barriers remain so a stale fragment arriving after deletion cannot erase a reviewed event choice.

### 2.15 Snapshot footer

```json
{"kind":"conversation-snapshot-footer","schemaVersion":2,"liveConversations":1,"tombstonedConversations":0,"payloadBytes":1804,"snapshotStateSha256":"a6cc84c3f37f8a4c7d20a570ef96be5d60ce1c9cf4b39d8869bc828282828282","snapshotPayloadSha256":"4b21f4c9f37f8a4c7d20a570ef96be5d60ce1c9cf4b39d8869bc818181818181"}
```

Counts must equal the header and observed lines. The payload hash must equal the filename.

### 2.16 Publication, fsync, and torn tails

A writer derives a candidate next sequence from its base head and constructs the complete sequence-specific batch in `journal/.tmp-<pid>-<nonce>` on the same filesystem. It writes the header and entries while hashing, writes the footer, calls `FileHandle.sync()`, closes the file, and does not yet report success. Inside the state-directory publication lock it re-reads the revision and confirms both the base revision and candidate sequence. It publishes with an atomic hard link from the fsynced temporary file to the final path; link creation fails if the immutable final name already exists. It then unlinks the temporary name and fsyncs the `journal/` directory. Success is returned only after the directory fsync. Node documents `FileHandle.sync()` as requesting that file data reach the storage device; the implementation must combine it with non-replacing publication, not stream completion or a replacing rename ([Node filesystem documentation](https://nodejs.org/api/fs.html#filehandlesync)).

Because the final name appears only after the footer is present and fsynced, a normal crash leaves either no final file, a `.tmp-*` file, or both names linked to the same complete inode. Readers ignore temporary names, and cleanup removes only the temporary link. A final-named file with a missing footer, extra bytes, count mismatch, or checksum mismatch is not a recoverable torn tail; it indicates storage corruption or an implementation defect. Readers stop and name the bad file. Recovery copies the same content-addressed object from the peer or verified backup, validates it, and republishes it. They never salvage a valid prefix of a batch, because that would violate batch atomicity.

Snapshots use the same write, file-fsync, non-replacing hard-link publication, and directory-fsync sequence. Compaction then writes `current.json.tmp-<pid>-<nonce>`, fsyncs it, renames it over `current.json`, and fsyncs `archive-v2/`. Replacing rename is used only for this compare-and-swapped ref, never for immutable objects. The old referenced snapshot remains present. Directory fsync is required on supported macOS filesystems; failure aborts publication.

## 3. Revision identity and concurrency

### 3.1 Revision calculation

For a validated `current.json`, active batches are every complete batch whose sequence is greater than `coveredThrough[writerId]`. Sort them by `(writerId, sequence, batchSha256)`. Multiple hashes for one `(writerId, sequence)` are corruption.

The revision is:

```text
SHA-256(
  UTF8("rocket-agents-archive-revision-v2\n")
  || exact current.json file bytes, including its one terminal LF
  || for each active batch: UTF8(batchSha256) || LF
)
```

It is a structural identity that is cheap to read: one small ref plus at most the batches accumulated since compaction. It is not a wall-clock revision and not a “latest conversation” hash.

### 3.2 Lost-update refusal

A normal importer does the following:

1. Opens a stable head inventory and records revision `R`.
2. Validates and prepares its entries outside the lock.
3. Acquires `~/.local/state/rocket-agents/conversations/archive.lock`.
4. Recomputes the current revision and next candidate sequence from canonical files.
5. If it is not `R`, deletes only its unpublished temporary file and throws `ConversationArchiveChangedError`. The caller retries from the new head.
6. Confirms the prepared sequence is still next, publishes one immutable batch by non-replacing link, fsyncs its directory, and releases the lock.

The lock makes retries uncommon; the compare is what prevents stale publication if the lock is bypassed or stale-lock recovery is wrong. This is the v2 equivalent of the manifest `contentSha256` check.

Two local appends prepared from one revision are not both accepted: one publishes and one refuses. Multiple installations may independently append from the same shared revision because they have distinct writer IDs and filesystems. Their batches are later unioned by transport; none overwrites another.

The lock protects only head inventory, sequence confirmation/allocation, final link, current-ref compare-and-swap, and pruning. It never covers source capture, input parsing, merge computation, snapshot construction, rsync, or Atrium ingestion.

### 3.3 Stable readers

A reader acquires the publication lock only long enough to validate `current.json`, list active final batch names, open file descriptors for the referenced snapshot and active batches, and calculate the revision. It then releases the lock and reads immutable open files. A later append is a different revision and is processed on the next run. A later prune cannot invalidate already-open descriptors.

## 4. Merge and materialization semantics

### 4.1 State union

For one conversation, union all snapshot state and journal operations as sets:

1. `removed` is the union of every tombstone's fragment hashes.
2. `active fragments` is every distinct fragment whose hash is not in `removed`.
3. Validate that all active fragments agree on `id`, `source`, and `sourceId`.
4. For each event ID, retain every distinct canonical event-byte variant and its contributing fragment hashes.
5. Union all resolution bodies and all superseded-resolution hashes. Remove superseded bodies from the active resolution set.
6. If the active resolutions name exactly one present chosen variant, select it. A later variant absent from that resolution's `observedEventSha256` produces an `unreviewed-event-variant` diagnostic but does not replace the choice. If there is no valid active resolution, select the lexicographically lowest canonical event bytes. Conflicting or dangling active resolutions use the deterministic fallback in section 2.9 and emit a structured diagnostic. No event conflict stops another conversation.
7. `events` is the selected distinct event set, sorted by `(timestamp || "", id)`.
8. Sort active fragments by `fragmentSha256`. `title` is the first title in that order. `workspace` is the first defined workspace in that order.
9. `startedAt` is the earliest event timestamp, else the earliest defined fragment `startedAt`. `updatedAt` is the latest event timestamp, else the latest defined fragment `updatedAt`.
10. `provenance.contentSha256` is `SHA-256("rocket-agents-conversation-state-v2\n" + sortedActiveFragmentHashesJoinedByLF + "\n")`.
11. `provenance.relativePath` is the sorted, duplicate-free fragment path list joined with `,`.
12. `provenance.redactions` is the sum across distinct active fragments.

These operations are commutative, associative, and idempotent. Replaying `A, B`, `B, A`, or `A, A, B` yields identical canonical bytes. The current pairwise `mergeConversationRecordFragments` can remain as a compatibility helper but must not be the journal reducer because its nested provenance hash is grouping-dependent.

The conflict policy is required by the current normalizer. `conversationEventFromRecord.ts` hashes only `index + NUL + redacted text`; `kind`, `role`, and `timestamp` are derived separately by `conversationEventKindFromRecord.ts`, `conversationRoleFromRecord.ts`, and `conversationTimestampFromRecord.ts` and are absent from the ID input. A normalizer or redactor deployment can therefore produce the same ID with different bytes on installations running different code. Capture output, `conversations:doctor`, and Atrium status report conversation ID, event ID, event hashes, fragment hashes, resolution state, and normalizer versions. The unresolved byte tie-break keeps the archive searchable and convergent; the section 2.9 operation makes a reviewed choice durable and prevents a stale normalizer from winning again. There is no automatic destructive repair.

### 4.2 Disposable Rocket Agents index

`archive-index.sqlite3` stores, at minimum:

- validated archive ID, current snapshot payload hash, and indexed revision;
- batch writer, sequence, hash, path, entry byte offset, and entry length;
- conversation ID, source, source ID, materialized record JSON, and record hash;
- fragment hash, descriptor fields, originating batch/offset, and active/tombstoned status;
- event ID, every canonical event variant/hash, the selected materialized variant, active/superseded resolution hashes, and the fragment hashes that contain each variant;
- removed fragment hashes even when no live record exists.

No field is canonical merely because it is in SQLite. On absence, schema mismatch, revision mismatch, failed integrity check, or conflicting offset/hash, Rocket Agents deletes or replaces only this state file and rebuilds it from `format.json`, the referenced snapshot, and active batches.

An append updates only conversations named by its entries after the canonical batch is durable. A crash between canonical publication and index update leaves a stale disposable index; the next open detects the revision mismatch and replays the missing batch.

### 4.3 Incremental source capture

The capture cache is `~/.local/state/rocket-agents/conversations/capture-index.sqlite3`. It is disposable: absence, failed `PRAGMA integrity_check`, schema mismatch, or normalizer-version mismatch causes a complete source pass. A failed or interrupted pass never advances a cache row. Losing the cache costs time but cannot lose an archived conversation. It is never authoritative evidence that its fragment hashes still exist in the current archive.

Each artifact row is keyed by `(source, relativePath, storageKind)` and stores:

- the `archiveId` into which the result was last successfully published;
- `device`, `inode`, and `birthtimeNs`, to distinguish replacement and inode reuse;
- `size`, `mtimeNs`, and `ctimeNs`, captured with bigint precision from an `O_NOFOLLOW` file descriptor;
- full-content SHA-256 from the last successful capture;
- capture normalizer version, redactor version, and source-adapter version;
- the fragment hashes emitted by that artifact;
- for JSONL, the last complete-LF byte offset, logical line index, cached normalized accumulator, prefix chunk hashes, and any incomplete tail bytes;
- for SQLite, the main database, `-wal`, and `-shm` fingerprints plus adapter-specific row cursors when the table has a safe monotonic key; and
- last success/error metadata for diagnostics.

The cache database metadata also records its schema version and last observed archive ID. Before granting any artifact hit, capture opens `archive-index.sqlite3`, requires that index to be validated at the exact current structural revision, requires the artifact row's archive ID to equal `format.json`, and performs indexed presence lookups for every cached fragment hash. A hash is present if the current normalized head contains either its active fragment descriptor or its observed-remove tombstone barrier. `archive-index.sqlite3`, not `capture-index.sqlite3`, answers this question because it is rebuildable from the canonical snapshot and batches. The cost is O(number of cached fragments for that artifact) primary-key lookups after the ordinary head/index revision check; it does not read or parse the source payload.

An archive-ID mismatch, stale/unvalidated archive index, or any absent cached fragment makes that artifact a cache miss and forces its normal full capture path. It is never reported as a hit. This covers same-ID reseeding to an older head as well as a different archive restored or migrated while the state directory survives. Cache rows are committed only after batch publication succeeds and the published fragment hashes are visible in an archive index advanced to the resulting revision. A crash before that point causes harmless recapture.

`path + size + mtime` is explicitly insufficient: a same-size in-place rewrite can preserve or restore mtime. On the supported local APFS hosts, an ordinary content edit changes `ctimeNs`; atomic replacement changes inode/birthtime; append changes size; and a sidecar-backed SQLite write changes at least the main/WAL/SHM fingerprint. Node exposes nanosecond bigint `mtimeNs`, `ctimeNs`, and `birthtimeNs`, and documents `write(2)` as changing both mtime and ctime ([Node stat-time documentation](https://nodejs.org/api/fs.html#stat-time-values)). Capture opens with `O_NOFOLLOW`, fstats before reading, reads/parses, fstats again, and commits the cache row only if both signatures match. A changed artifact therefore cannot receive an unchanged cache hit through the normal filesystem API. Tests cover same-size rewrite with restored mtime, atomic replacement, append, truncation, WAL-only mutation, symlink substitution, and mutation during read.

Discovery still enumerates configured roots and fstats known artifacts. That metadata scan is O(number of artifact paths), but it reads no unchanged payload, allocates no unchanged records, performs no JSON parsing/redaction, and writes no export slice. The expensive work and bytes read/written are proportional to changed artifacts. A future filesystem watcher may reduce metadata enumeration, but correctness must not depend on a watcher delivering every event.

Capture behavior by storage kind is:

- **Unchanged artifact:** exact full fingerprint and version match, row/archive IDs match, and every cached fragment hash has current-head presence evidence; reuse cached fragment hashes and do not open payload content.
- **JSON or Tauri artifact changed:** parse, redact, normalize, and hash that artifact in full. No other artifact is revisited.
- **JSONL artifact grew:** first compare cached SHA-256 hashes for every fixed-size prefix chunk by reading bytes only. If every prefix chunk and the cached incomplete-tail boundary match, resume JSON parsing at the last complete LF with the cached global line index and normalized accumulator; do not parse or redact the prefix. Hashing the prefix for this proof is allowed, but parsing it is not. If any prefix chunk differs, the file shrank, the inode/birthtime changed, or the boundary is inconsistent, discard the checkpoint and fully reparse that artifact.
- **SQLite artifact changed:** use a provider adapter's monotonic row/update cursor only when its schema proves inserts/updates cannot occur behind that cursor. Otherwise reopen the database read-only and fully recapture that one database. Main/WAL/SHM before/after fingerprints must remain stable for the cache transaction to commit.
- **Artifact disappeared:** remove only its cache row after recording the absence. Source absence never emits an archive tombstone.

The scheduled path becomes `conversations:capture --append-to <archive-v2>`. It emits one batch containing only new fragment hashes and explicit operations. A no-op capture publishes no batch. Its machine-readable metrics include discovered, statted, cache-hit, fully parsed, tail-resumed, payload bytes read, prefix-verification bytes, records normalized, fragments appended, elapsed time, and peak RSS.

## 5. Compaction

### 5.1 Trigger

Automatic compaction is requested when any condition is true:

- complete active journal bytes are at least `max(512 MiB, 25% of referenced snapshot bytes)`;
- there are at least 512 active batches; or
- at least 20% of fragment descriptors are tombstoned.

`conversations:compact --force` requests it explicitly. The scheduler checks thresholds after a successful append; it does not compact hourly merely because it ran.

### 5.2 Algorithm and atomicity

1. Record base revision `R` and the contiguous frontier of all valid active batches.
2. Rebuild or verify the disposable index at `R`.
3. Stream normalized conversation states in conversation-ID order into a new snapshot temporary file. Store event bodies once per conversation and preserve fragment/event origin membership, event-resolution bodies/barriers, removed-fragment barriers, and archive peer membership.
4. Validate the completed snapshot independently, including reconstructing every `record`, counts, state hash, payload hash, and frontier.
5. Fsync the snapshot and rename it to its content-addressed final name; fsync `snapshots/`.
6. Prepare deterministic `current.json` for that snapshot and frontier.
7. Acquire the publication lock and recompute the revision. If it is not `R`, keep the valid unreferenced snapshot as a reusable object, do not change `current.json`, and return `ConversationArchiveChangedError` for a retry.
8. Atomically replace and fsync `current.json` as specified above.
9. Release the lock. Readers holding the old snapshot and batch descriptors continue safely; new readers use the new head.

Compaction does not immediately delete covered batches or the prior snapshot. They remain valid recovery and sync objects until peer acknowledgement permits pruning.

### 5.3 Peer acknowledgement and pruning

After a sync, each installation writes an ephemeral acknowledgement keyed by `(archiveId, peerWriterId)`, never by the SSH route used. It contains that identity, exact `current.json` hash, snapshot hash, frontier, verified time, and protocol/build versions. The acknowledgement quorum is the active observed-remove enrollment set from section 2.10. A configured target with no archive has no enrollment and is excluded; `portatil-usb` and `portatil` count once if both return the same writer ID. A route that unexpectedly returns a different identity stops rather than silently enlarging the set.

Covered batches have a 24-hour minimum local retention floor and a 30-day no-ack ceiling, both measured from the first validated local observation of the snapshot that covers them. Local wall-clock time affects only how long extra immutable recovery objects are retained, never merge order or canonical state. After 24 hours, a covered batch may be pruned when every active enrolled peer has acknowledged the covering frontier. After 30 days, it may be pruned without an absent peer's acknowledgement if the current snapshot has passed deep validation, the immediately previous validated snapshot is retained, and the batch sequence is at or below the current snapshot frontier. Losing `retention.json` or acknowledgements restarts both timers; it never accelerates deletion. This bounds normal journal retention while making the penalty for a long-absent peer a full snapshot transfer rather than unbounded growth.

An operator may instead run `conversations:forget-peer` after reviewing the peer's last acknowledgement and unmerged frontier. Retirement removes it from the acknowledgement quorum but does not shorten the 24-hour minimum or erase its causal frontier. An enrolled peer absent for weeks is never auto-retired: automatic identity deletion could discard the only route to unseen events. If it returns after covered batches were pruned, sync first stages and validates every locally unique batch/snapshot it still has, reconciles those objects on a healthy peer, and then transfers the full current snapshot. A retired identity follows the stricter quarantine/rotation path in section 2.10.

Pruning runs under the publication lock, resolves an explicit list of covered content-addressed paths, unlinks only those paths, and fsyncs the affected directories. It retains at least the current and immediately previous validated snapshots. It never manufactures missing journal history.

### 5.4 Concurrent compaction cases

- **Appender during local compaction:** the appender wins or compaction wins the compare-and-swap. The loser retries; no entry is overwritten.
- **Reader during compaction:** it finishes against its open immutable revision.
- **Remote appender while this host compacts:** both operations succeed independently. Sync applies the remote batch above the compacted frontier.
- **Multiple installations compact divergent heads:** no snapshot is last-writer-wins. Pairwise sync joins normalized snapshot states and all uncovered batches. If one snapshot can be used as a base with a complete suffix, every installation deterministically selects it. Otherwise reconciliation performs one exceptional full materialization and emits a new deterministic joined snapshot.

## 6. Atrium ingestion

### 6.1 Cursor definition

Atrium adds disposable tables for one archive identity, one snapshot cursor, per-writer batch cursors, and normalized fragment/event state. The cursor consists of:

- `archive_id`;
- `snapshot_payload_sha256` and `snapshot_state_sha256`;
- the snapshot `coveredThrough` vector;
- for each writer: last fully applied sequence and batch hash;
- while a large validated batch is being applied: its hash, next entry byte offset, and next entry index.

This tuple is the high-water mark. A raw byte offset by itself is not sufficient because compaction replaces the base and two writers have independent sequences. Cursor changes commit in the same SQLite transaction as the records produced by those entries.

### 6.2 Incremental ingestion

1. Validate `format.json`, `current.json`, the referenced snapshot identity, and active batch footers before applying data.
2. If the stored snapshot identity matches, enumerate each writer's contiguous batches after its cursor. A gap pauses only that writer; another writer may advance.
3. Validate an entire batch checksum before applying its first entry.
4. Apply idempotent fragment/tombstone operations to Atrium's derived archive-state tables, rematerialize only affected conversations, call the existing `write_conversation`, and advance the cursor in the same transaction.
5. A transaction ends at the first boundary reached after at least one complete entry: 64 batches, 10,000 entries, or 32 MiB of entry-line bytes. One entry larger than 32 MiB is allowed as a one-entry transaction.
6. On crash, the cursor either advanced with the data or did not. Replay is safe because fragment and tombstone hashes are set keys.

Atrium duplicates the materialization algorithm only as derived logic. Rocket Agents supplies cross-language fixtures containing permutations, duplicates, divergent host fragments, tombstones, event conflicts, and snapshot states. Both implementations must produce the same materialized record bytes and hashes.

### 6.3 Cursor invalidation and full reconciliation

The cursor is invalid when:

- archive ID changes;
- `current.json` references a different snapshot payload hash, including after compaction;
- the referenced snapshot or any needed batch fails validation;
- the new frontier moves behind the stored cursor;
- one writer/sequence maps to a different batch hash; or
- derived archive-state integrity checks fail.

A changed snapshot within the same archive is the normal full-compaction signal. Atrium reads the snapshot and post-frontier batches, reconstructs all live conversations, and invokes its existing full reconciliation behavior: `write_conversation` for every live ID followed by `delete_absent_conversations` per represented provider. That pass remains one all-or-nothing SQLite transaction so malformed input cannot leave a half-reconciled searchable index. The cursor is reset in that same commit. This O(corpus) pass happens on compaction, not every refresh.

An archive-ID change is not silently accepted as compaction. The CLI reports it and requires `atrium ingest --rebuild-archive-state`, which removes only disposable archive-derived state before the same full reconciliation. Notes, synthesis registry data, and canonical Rocket Agents files are not deleted.

## 7. Multi-installation sync

### 7.1 Deployed routes and archive peer identity

The deployment has one local Mac scheduler and three configured target routes, not one fixed remote peer. The installed `com.cristian.sync-all-safe` LaunchAgent runs at 14:00 daily and calls `sync-conversations` for `neo`, then exactly one of `portatil-usb` or `portatil`, then `macmini`, subject to reachability. The two `portatil` aliases are cable and Wi-Fi routes to the same laptop. The source `launchd/com.cristian.sync-conversations.plist` exists but is not installed; it is not a live scheduler. `com.cristian.atrium-refresh` is independently installed hourly, and the Claude SessionEnd hook can start the same refresh between timer runs.

Configured route and archive peer are deliberately separate concepts:

- `sync-conversations peer-info --json` returns `archivePresent`, optional v2 `archiveId`, durable `writerId`, format, head/manifest identity, protocol version, and build version without capturing or writing.
- The orchestrator probes every route, groups v1 routes by the preflight writer ID and v2 routes by `(archiveId, writerId)`, and stops if two supposed aliases disagree. Acknowledgement and membership use the bound v2 identity.
- A target returning `archivePresent:false` is not seeded or enrolled by a normal scheduled sync. Initial seeding requires `--enroll-peer`, a distinct durable writer identity, full validation, and the self-enrollment entry from section 2.10.
- `neo` is therefore a configured route but not part of the archive quorum while it has no archive. Its checkout or disk-health failure remains an orchestrator error to report, not a reason to retain conversation batches forever.

`sync-all-safe` invokes `remote_config` after conversation sync on the Mac routes. Pairwise sync can therefore begin while installations are on different Rocket Agents commits. The protocol handshake refuses incompatible archive schemas and records normalizer/redactor/adapter build versions; compatible version skew remains mergeable and may produce the event variants specified in sections 2.9 and 4.1.

The installed cadence makes convergence a checked daily event, not a continuous invariant. Local capture may advance the archive between syncs. A non-zero `dry` before a scheduled or manual sync is ordinary drift; only the immediate sync-then-dry acceptance window is expected to be zero. A dated operational check also found a stale local `~/.local/state/sync-all-safe.lock`: runs after that point logged `another sync is running, skipping heavy sync` and did not attempt any target. Migration preflight must therefore verify both scheduler labels and lock ownership; schedule presence is not evidence that daily convergence occurred.

### 7.2 Transport algorithm

`sync-conversations <host> sync` becomes an object exchange and head reconciliation:

1. Refuse while `migration.freeze` exists in normal modes. The explicit `--migration-frozen` mode requires the sentinel on both endpoints and skips provider capture; for v1 it merges only existing canonical archives, and for v2 it seeds/verifies immutable objects. Acquire the existing local and remote state-directory sync locks.
2. Ask Rocket Agents on both endpoints for peer info and a validated inventory: installation writer ID, archive ID, exact head revision, current ref, snapshot objects, batch `(writer, sequence, hash, bytes)` objects, active/retired peer membership, and identity-keyed acknowledgements. Do not trust aliases or filenames without identity/footer validation.
3. If only one endpoint has v2, normal sync stops. `--enroll-peer` may seed the other from its format file, current snapshot, and active batches, create a distinct local writer identity there, deep-validate, and append self-enrollment. If non-empty archive IDs differ, stop for operator reconciliation.
4. Compute missing immutable objects in both directions. Use `rsync --files-from`, `--ignore-existing`, `--partial-dir` inside the run's state transfer directory, `--no-owner`, `--no-group`, and a timeout. Rsync documents that `--ignore-existing` leaves existing destination files untouched and that a partial directory keeps interrupted data out of final paths ([rsync manual](https://download.samba.org/pub/rsync/rsync.1)). Never use `--inplace`, `--append`, or `--delete`.
5. Receive every object under `~/.local/state/.../transfers/<run-id>/`. Rocket Agents validates the complete checksum and expected archive identity, then publishes it with exclusive create, fsync, rename, and directory fsync. Rsync never writes directly into the canonical directory.
6. Reconcile heads from the union. Prefer a valid snapshot whose frontier maximizes total covered sequences and for which every required suffix batch is present; break equal-frontier ties by the lowest snapshot payload hash. If incomparable snapshots cannot supply a complete suffix, join their normalized state and emit one deterministic snapshot. Apply every batch above the chosen frontier.
7. Under each endpoint's publication lock and with a compare against the inventory revision, install identical deterministic `current.json` bytes. A local append that slipped in causes reconciliation to retry; it is not overwritten.
8. Run semantic verification on both endpoints. Success requires identical archive ID, structural revision, live conversation count, sorted-ID hash, per-ID event-set digest, materialized state digest, and peer membership digest.
9. Write acknowledgements keyed by each endpoint's `(archiveId, writerId)`. Optional pruning follows section 5.3; route names never enter the quorum.

`dry` performs identity inventory, checksum validation, a no-write union plan, and semantic comparison. It reports `added`, `updated`, and `removed` conversation states plus missing objects and estimated transfer bytes. In the immediate post-sync acceptance window all change counts and missing-object counts are zero; between daily syncs they need not be.

The common case transfers only new batch files. Directory inventories and small JSON responses are exchanged, but the 3.4 GB snapshot is not recopied. A new snapshot is transferred once after compaction.

### 7.3 Failure matrix

| Failure or race | Required result |
| --- | --- |
| Multiple peers append from the same shared revision | Distinct writer IDs produce distinct immutable batches; pairwise sync unions them and every peer materializes the same event set. |
| Multiple peers append different revisions of one conversation | All fragment hashes remain active; event union contains every non-conflicting event from every peer. |
| One host compacts while the other appends | The compaction snapshot becomes a candidate base and the remote batch remains above its writer frontier. Neither is overwritten. |
| Clock skew | No correctness effect. Timestamps are informational; hashes, writer IDs, sequences, and frontiers decide identity and coverage. |
| Transfer interruption | Only state-directory `.part` files exist. No canonical ref changes. Retry resumes or retransfers, validates, then publishes. |
| Source host compacts or prunes during transfer | Sync and publication locks plus revision compare force inventory retry. Pruning cannot run without peer acknowledgement. |
| Same writer and sequence, different hashes | Hard corruption error. Do not select by time, size, or host. Preserve both files in state quarantine for diagnosis. |
| Divergent compactions | Join normalized snapshot states and uncovered batches; emit a deterministic union snapshot if no candidate has a complete suffix. |
| Peer restored from a stale backup after pruning | Transfer the full current snapshot and active suffix. Never lower the healthy host's frontier. |
| Two SSH aliases reach the same installation | Matching archive/writer identity collapses them to one peer and one acknowledgement. A mismatch stops as route misconfiguration. |
| Configured target has never held this archive | Report `not-enrolled`; do not include it in the acknowledgement quorum or seed it without `--enroll-peer`. |
| Enrolled peer is absent beyond the 30-day no-ack ceiling | Prune covered objects under section 5.3 and require full-snapshot reseeding when it returns; do not discard its causal frontier. |
| Retired peer returns | Refuse normal sync; quarantine/import unique objects, rotate identity, full-seed, and explicitly re-enroll. |
| Daily job is skipped or fails | Archives may drift normally. Health reports the last successful identity-based sync; only explicit sync-then-dry establishes convergence. |
| Compatible peers run different normalizers | Retain variants and honor durable resolutions. Incompatible archive protocol versions refuse before transfer. |
| Final object checksum mismatch | Stop before publication; keep the existing valid object and report the bad transfer. |
| Sync dies after objects publish but before head reconciliation | Objects are harmless unreferenced or active immutable inputs. The next sync inventories and reconciles them. |

## 8. Lossless migration and rollback

### 8.1 Preconditions

The migration release must already be installed at the same verified commit on every distinct archive-holding Mac, including freeze-sentinel checks in `sync-conversations`, the canonicalized `atrium-refresh`, and the SessionEnd hook. Do not rely on the daily `remote_config` path to deploy it, because that path runs after conversation sync and may itself be skipped. Both repositories must pass their gates before touching live data.

Before freezing, create an unbound durable writer identity on each v1 archive holder with `pnpm run conversations:writer-init -- --create-unbound`, then run `sync-conversations peer-info --json` locally and over every configured route from `sync-all-safe`: `neo`, `portatil-usb`, `portatil`, and `macmini`. Save the read-only report under migration state, group matching writer IDs across routes, and identify every target with a readable v1 or v2 archive. For this deployment, the intended migration set is the local installation plus the distinct archive-holding `portatil` and `macmini` installations; the two `portatil` routes count once. `neo` is excluded only by a successful probe proving `archivePresent:false`, not merely by being unreachable or unhealthy. A known archive holder that is unreachable blocks migration: do not assume it has no unique events, and do not cut over the reachable subset. An operator may proceed only after that installation is reachable and inventoried or after its latest archive and semantic inventory are recovered from a verified backup.

Drift discovered by `dry` before the freeze is normal because capture runs between daily syncs. Convergence is established only after every archive writer is frozen, using the frozen v1 merge in section 8.2.

On every archive-holding Mac, create the sentinel first, wait for any active writer to finish, boot out the two actually installed LaunchAgents, and verify all known writer labels are absent:

```bash
mkdir -p "$HOME/.local/state/rocket-agents/conversations"
install -m 600 /dev/null "$HOME/.local/state/rocket-agents/conversations/migration.freeze"
if pgrep -fal '[s]ync-all-safe|[s]ync-conversations|[a]trium-refresh|run-conversations-(export|import|capture)|conversations.*compact'; then
  echo "wait for active conversation writers before bootout" >&2
  exit 1
fi
launchctl bootout "gui/$(id -u)/com.cristian.sync-all-safe"
launchctl bootout "gui/$(id -u)/com.cristian.atrium-refresh"
for label in com.cristian.sync-all-safe com.cristian.sync-conversations com.cristian.atrium-refresh; do
  if launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; then
    echo "conversation writer remains scheduled: $label" >&2
    exit 1
  fi
done
cd "$HOME/p/rocket-agents"
pnpm run conversations:locks -- --check
"$HOME/p/dotfiles/bin/conversation-writers" verify-frozen
```

If the first `pgrep` reports an existing writer, wait and repeat before `bootout`; do not terminate it during publication. The SessionEnd hook and `atrium-refresh` must read `migration.freeze` before detaching or capturing. `conversation-writers verify-frozen` checks the sentinel, all three labels, the installed hook command, the Atrium lock, Rocket Agents `archive.lock`/`sync.lock`, and the `sync-all-safe.lock` owner. A stale `sync-all-safe.lock` is reported separately and may be removed only by the explicit `conversation-writers clear-stale-lock` operation after proving no matching process exists. The freeze remains on every required installation until every verification below passes.

### 8.2 Ordered migration

1. With writers frozen, establish the v1 convergence baseline by merging only the existing canonical archives; provider export remains disabled. For each distinct required peer route, run frozen sync and dry in a full cycle, then repeat cycles until two consecutive complete cycles report `added: 0, updated: 0` and identical manifest `contentSha256` for every installation:

   ```bash
   sync-conversations portatil sync --migration-frozen --format v1
   sync-conversations macmini sync --migration-frozen --format v1
   sync-conversations portatil dry --migration-frozen --format v1
   sync-conversations macmini dry --migration-frozen --format v1
   ```

   Use whichever `portatil` route returned the enrolled installation identity in preflight. A later peer can add events to the local archive after an earlier peer was checked, which is why the whole cycle repeats and why a single pairwise zero is insufficient. If any required peer becomes unreachable, stop; keep v1 and the freeze intact or abort by unfreezing v1 without creating a cutover.
2. Record immutable source metadata and copy the v1 file without removing it:

   ```bash
   STATE="$HOME/.local/state/rocket-agents/conversations/migration"
   ARCHIVE="$HOME/.local/share/rocket-agents/conversations/archive.jsonl"
   mkdir -p "$STATE"
   stat -f '%z' "$ARCHIVE" > "$STATE/v1.bytes"
   shasum -a 256 "$ARCHIVE" > "$STATE/v1.file.sha256"
   sed -n '1p' "$ARCHIVE" > "$STATE/v1.manifest.json"
   cp -p "$ARCHIVE" "$HOME/.local/share/rocket-agents/conversations/archive-v1-pre-v2.jsonl"
   shasum -a 256 -c "$STATE/v1.file.sha256"
   ```

   The final command verifies the original remains unchanged. A second checksum file for the backup is written by `conversations:migrate-v1` and must equal the original file hash.
3. On one host only, create v2 with exclusive output paths:

   ```bash
   cd "$HOME/p/rocket-agents"
   pnpm run conversations:migrate-v1 -- \
     --input "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" \
     --output "$HOME/.local/share/rocket-agents/conversations/archive-v2" \
     --report "$HOME/.local/state/rocket-agents/conversations/migration/v2-migration.json"
   pnpm run conversations:writer-init -- \
     --archive "$HOME/.local/share/rocket-agents/conversations/archive-v2" --bind
   pnpm run conversations:enroll-peer -- \
     --archive "$HOME/.local/share/rocket-agents/conversations/archive-v2" --self --apply
   ```

4. Produce independent before/after semantic inventories:

   ```bash
   pnpm run conversations:verify-v1 -- \
     --archive "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" \
     --output "$STATE/v1.semantic.jsonl"
   pnpm run conversations:verify-v2 -- \
     --archive "$HOME/.local/share/rocket-agents/conversations/archive-v2" \
     --output "$STATE/v2.semantic.jsonl"
   pnpm run conversations:compare-semantic -- \
     --before "$STATE/v1.semantic.jsonl" \
     --after "$STATE/v2.semantic.jsonl" \
     --require-records 27041 \
     --require-id-equality \
     --require-event-set-equality \
     --require-event-byte-equality \
     --require-metadata-equality \
     --require-fragment-provenance-preserved
   ```

   Each semantic inventory has one sorted line per ID containing source/source ID, title/workspace/start/end metadata, event count, every event ID and canonical event-byte hash, and the original fragment provenance triple. Its footer contains record count, total distinct event count, sorted-ID hash, and event-set digest. The comparison enumerates any missing ID, event, event-byte variant, metadata value, or provenance value; global hash equality alone is not accepted. This proves that all 27,041 conversations, including the 4,617 with no remaining source rollout, crossed the boundary.

   Full materialized-record byte equality is deliberately not an acceptance criterion. Section 4.1 gives the union state a new deterministic provenance hash and a sorted path union, so a migrated v2 materialization is not byte-identical to its v1 record even when it has one fragment. The v2 initial `snapshotStateSha256` is recorded but is not required to equal the v1 manifest `contentSha256`; requiring either equality would make the migration command fail by construction. Losslessness is instead proved over every user-bearing and lineage-bearing field listed above.
5. Run the v2 validator twice, once using the normal index and once after deleting only a copy of the disposable index, to prove rebuildability:

   ```bash
   pnpm run conversations:verify-v2 -- --archive "$HOME/.local/share/rocket-agents/conversations/archive-v2" --deep
   pnpm run conversations:verify-v2 -- --archive "$HOME/.local/share/rocket-agents/conversations/archive-v2" --deep --rebuild-index
   ```

6. Seed every other required frozen installation, one identity rather than one alias at a time, using `sync-conversations <route> sync --migration-frozen --format v2 --enroll-peer`. This mode is permitted only when both endpoints have the sentinel, skips provider capture, exchanges/reconciles immutable v2 objects, binds the peer's preflight writer identity to this archive, deep-validates the received head, and appends that peer's self-enrollment. The identity file is never transported. Repeat `verify-v2` and `compare-semantic` on every peer. A required peer becoming unreachable blocks this step; `neo` is not seeded merely because it appears in `sync-all-safe`.
7. Rebuild a disposable Atrium test index from v2 and compare provider/conversation/record counts with the production index. Budget this as a required one-time full raw-index rewrite: `to_records` copies materialized `provenance.contentSha256` into every raw row's `source_sha256`, and `write_conversation` compares that column, so the provenance change makes every migrated raw conversation appear changed. Measure the exact row count, elapsed time, WAL growth, and free-space requirement on an index copy before cutover. This rebuilds the raw `records` rows and both FTS lanes. It does **not** re-embed all raw rows: Atrium's `SEMANTIC_ROLES` is only `note` and `synthesis`, while raw conversation roles are lexical-only. Existing note/synthesis vectors are outside this raw-provider rewrite and must remain unchanged. Then run `pytest tests/ -q` in Atrium.
8. Run frozen v2 sync across every distinct peer route, then repeat the complete dry cycle twice. Acceptance on every installation is zero planned changes, zero missing objects, distinct writer IDs, identical active peer-membership digest, identical structural revision, identical per-ID event-set digest, and identical state digest.
9. Remove the freeze sentinel on every required installation only after all reports are archived in state. Bootstrap the actual daily sync orchestrator and hourly refresh agent on each Mac, trigger one guarded refresh locally, then run one explicit multi-peer sync/dry cycle. Do not bootstrap the uninstalled legacy conversation plist and do not kickstart `sync-all-safe`, because that script also performs unrelated Git and configuration writes:

   ```bash
   rm "$HOME/.local/state/rocket-agents/conversations/migration.freeze"
   launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cristian.sync-all-safe.plist"
   launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.cristian.atrium-refresh.plist"
   "$HOME/.local/bin/atrium-lock" "$HOME/.local/state/atrium/refresh.lock" \
     "$HOME/.local/bin/atrium-refresh"
   sync-conversations portatil sync
   sync-conversations macmini sync
   sync-conversations portatil dry
   sync-conversations macmini dry
   ```

   Use the selected physical-laptop route and repeat sentinel removal/bootstrap on every required peer before normal sync. If a job is already bootstrapped, `launchctl bootstrap` reports that condition; verify it with `launchctl print` rather than using `kickstart -k` during migration. Re-run `conversation-writers verify-running` and require the daily and hourly labels plus the guarded SessionEnd hook to match the expected deployment.
10. Keep `archive.jsonl` and `archive-v1-pre-v2.jsonl` read-only. No migration or scheduler deletes them automatically. Retention or deletion is a separate, explicitly approved operation after backups and at least one full recovery drill.

### 8.3 Rollback

Before unfreezing, rollback is simply: leave v1 untouched, move the unreferenced `archive-v2` directory to a timestamped quarantine name, deploy the prior code on every required installation, and re-bootstrap `com.cristian.sync-all-safe` and `com.cristian.atrium-refresh`. No canonical v1 byte changes.

After v2 writers have been unfrozen, rollback must first freeze all three triggers again. Export current v2 materialized state to a new v1 temporary file, validate its manifest and per-ID/event equality against v2, fsync it, back up the old `archive.jsonl`, atomically rename the new file to `archive.jsonl`, fsync the data directory, and only then deploy the prior code. Never roll back by merely pointing old code at the pre-migration v1 file, because that would omit conversations appended after cutover.

## 9. File-by-file implementation plan

No existing migration or legacy reader file is deleted in the migration release. Deletion is deferred until the retained v1 rollback window is explicitly closed.

### 9.1 Rocket Agents: new files

Each TypeScript source below contains exactly one exported top-level declaration and one responsibility.

- `scripts/lib/conversations/types/ConversationArchiveFormat.ts` — schema for immutable `format.json`.
- `scripts/lib/conversations/types/ConversationArchiveHead.ts` — schema for `current.json`.
- `scripts/lib/conversations/types/ConversationArchiveFrontierEntry.ts` — one writer/sequence frontier element.
- `scripts/lib/conversations/types/ConversationBatchHeader.ts` — batch header schema.
- `scripts/lib/conversations/types/ConversationBatchFooter.ts` — batch footer schema.
- `scripts/lib/conversations/types/ConversationFragmentEntry.ts` — fragment entry schema.
- `scripts/lib/conversations/types/ConversationTombstoneEntry.ts` — tombstone entry schema.
- `scripts/lib/conversations/types/ConversationSnapshotHeader.ts` — snapshot header schema.
- `scripts/lib/conversations/types/ConversationSnapshotFooter.ts` — snapshot footer schema.
- `scripts/lib/conversations/types/ConversationSnapshotLiveState.ts` — normalized live state schema.
- `scripts/lib/conversations/types/ConversationSnapshotTombstonedState.ts` — anti-resurrection state schema.
- `scripts/lib/conversations/types/ConversationEventVariant.ts` — one retained canonical payload variant and its fragment origins.
- `scripts/lib/conversations/types/ConversationEventVariantResolutionEntry.ts` — durable reviewed variant choice and supersession set.
- `scripts/lib/conversations/types/ConversationPeerEnrollmentEntry.ts` — self-authored archive membership schema.
- `scripts/lib/conversations/types/ConversationPeerRetirementEntry.ts` — observed-remove peer membership schema.
- `scripts/lib/conversations/types/ConversationSnapshotPeerMembership.ts` — compacted active/retired membership state.
- `scripts/lib/conversations/types/ConversationArtifactFingerprint.ts` — bigint-precision file/database-sidecar identity used by capture cache.
- `scripts/lib/conversations/types/ConversationCaptureCheckpoint.ts` — versioned JSONL or database resume state.
- `scripts/lib/conversations/types/ConversationWriterIdentity.ts` — durable host-local writer identity schema.
- `scripts/lib/conversations/serializeCanonicalConversationRecord.ts` — fixed-order record serialization shared by all hashes.
- `scripts/lib/conversations/hashConversationFragment.ts` — fragment identity calculation.
- `scripts/lib/conversations/materializeConversationState.ts` — set-based deterministic reducer.
- `scripts/lib/conversations/readConversationArchiveHead.ts` — validated stable head inventory and open immutable descriptors.
- `scripts/lib/conversations/listActiveConversationBatches.ts` — frontier-aware batch enumeration and collision/gap checks.
- `scripts/lib/conversations/validateConversationBatch.ts` — byte/count/footer/filename validation.
- `scripts/lib/conversations/writeConversationBatch.ts` — temp write, checksum, fsync, revision compare, and atomic publication.
- `scripts/lib/conversations/validateConversationSnapshot.ts` — reconstruct and validate all snapshot hashes and states.
- `scripts/lib/conversations/writeConversationSnapshot.ts` — deterministic compacted snapshot writer.
- `scripts/lib/conversations/compactConversationArchive.ts` — threshold check, snapshot build, and current-ref CAS.
- `scripts/lib/conversations/ConversationArchiveIndex.ts` — disposable native-Node-SQLite index with rebuild and incremental replay.
- `scripts/lib/conversations/ConversationCaptureIndex.ts` — disposable artifact fingerprints, fragment mappings, and parser checkpoints.
- `scripts/lib/conversations/fingerprintConversationArtifact.ts` — stable `O_NOFOLLOW` pre/post stat and SQLite-sidecar fingerprint.
- `scripts/lib/conversations/resumeJsonlConversationArtifact.ts` — prefix-verified suffix parsing with cached line/event accumulator.
- `scripts/lib/conversations/captureConversationArtifactsIncrementally.ts` — cache-hit routing and changed-artifact capture orchestration.
- `scripts/lib/conversations/hasPublishedConversationFragments.ts` — exact-head archive-index presence check for cached fragment hashes.
- `scripts/lib/conversations/readConversationWriterIdentity.ts` — validate durable local identity and refuse silent replacement.
- `scripts/lib/conversations/createConversationTombstone.ts` — preview exact observed-remove fragment set.
- `scripts/lib/conversations/createConversationRedactionBatch.ts` — atomically pair sanitized replacement with superseded-fragment tombstone.
- `scripts/lib/conversations/createConversationRepairBatch.ts` — validate an explicit reviewed repair plan without inferring deletions.
- `scripts/lib/conversations/resolveConversationEventConflict.ts` — preview canonical variants and append a base-revision-checked durable resolution.
- `scripts/lib/conversations/materializeConversationPeerMembership.ts` — observed-remove enrollment reducer independent of route names.
- `scripts/lib/conversations/enrollConversationArchivePeer.ts` — self-enroll a validated seeded writer identity.
- `scripts/lib/conversations/forgetConversationArchivePeer.ts` — preview and append explicit peer retirement without deleting frontier state.
- `scripts/lib/conversations/migrateConversationArchiveV1.ts` — exclusive, lossless v1-to-v2 snapshot creation.
- `scripts/lib/conversations/writeConversationSemanticInventory.ts` — per-ID/event/record verification inventory.
- `scripts/lib/conversations/compareConversationSemanticInventories.ts` — exact before/after mismatch reporter.
- `scripts/lib/conversations/reconcileConversationArchiveObjects.ts` — deterministic union/head selection for sync.
- `scripts/lib/conversations/publishReceivedConversationObject.ts` — validate and atomically accept one transferred object.
- `scripts/commands/conversationsCompact.ts` — compact CLI argument parsing and result rendering.
- `scripts/commands/conversationsMigrateV1.ts` — migration CLI.
- `scripts/commands/conversationsVerifyV1.ts` — v1 semantic inventory CLI.
- `scripts/commands/conversationsVerifyV2.ts` — v2 structural and semantic verifier CLI.
- `scripts/commands/conversationsCompareSemantic.ts` — equality CLI.
- `scripts/commands/conversationsInventory.ts` — machine-readable sync inventory CLI.
- `scripts/commands/conversationsReconcile.ts` — transferred-object reconciliation CLI.
- `scripts/commands/conversationsLocks.ts` — read-only lock ownership check for migration.
- `scripts/commands/conversationsCapture.ts` — incremental capture/append CLI and machine-readable metrics.
- `scripts/commands/conversationsTombstone.ts` — preview-first explicit deletion CLI.
- `scripts/commands/conversationsRedact.ts` — preview-first replacement/redaction CLI.
- `scripts/commands/conversationsRepair.ts` — reviewed-plan migration repair CLI.
- `scripts/commands/conversationsResolveEventConflict.ts` — diagnostic and explicitly applied conflict repair CLI.
- `scripts/commands/conversationsWriterInit.ts` — first initialization or explicit identity recovery/rotation CLI.
- `scripts/commands/conversationsEnrollPeer.ts` — self-enrollment CLI after validated seed/bind.
- `scripts/commands/conversationsForgetPeer.ts` — preview-first peer retirement CLI.
- `scripts/commands/conversationsPeerInfo.ts` — read-only route identity/archive inventory CLI.
- `scripts/bin/run-conversations-compact.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-migrate-v1.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-verify-v1.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-verify-v2.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-compare-semantic.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-inventory.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-reconcile.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-locks.ts` — one-call command entrypoint.
- `scripts/bin/run-conversations-capture.ts` — one-call incremental capture entrypoint.
- `scripts/bin/run-conversations-tombstone.ts` — one-call explicit tombstone entrypoint.
- `scripts/bin/run-conversations-redact.ts` — one-call redaction entrypoint.
- `scripts/bin/run-conversations-repair.ts` — one-call reviewed repair entrypoint.
- `scripts/bin/run-conversations-resolve-event-conflict.ts` — one-call conflict-resolution entrypoint.
- `scripts/bin/run-conversations-writer-init.ts` — one-call durable identity entrypoint.
- `scripts/bin/run-conversations-enroll-peer.ts` — one-call self-enrollment entrypoint.
- `scripts/bin/run-conversations-forget-peer.ts` — one-call retirement entrypoint.
- `scripts/bin/run-conversations-peer-info.ts` — one-call read-only identity entrypoint.

### 9.2 Rocket Agents: changed files

- `package.json` — add capture, compact, tombstone, redact, repair, conflict-resolution, writer-identity, peer-info/enroll/forget, migrate, verify, compare, inventory, reconcile, and lock scripts without dependencies.
- `scripts/lib/conversations/importConversationExport.ts` — validate an input export, create only unseen fragments/tombstones, and publish one v2 batch with revision refusal instead of loading and rewriting the corpus.
- `scripts/lib/conversations/exportConversations.ts` — retain portable v1 full export for migration/interchange; scheduled v2 refresh moves to the incremental capture command rather than adding a superficial append flag here.
- `scripts/lib/conversations/captureConversations.ts` — use the persistent capture index instead of an always-empty map for v2 capture.
- `scripts/lib/conversations/captureConversationArtifacts.ts` — delegate scheduled capture to fingerprint/checkpoint routing while preserving an explicit full-export path.
- `scripts/lib/conversations/readArchiveRevision.ts` — calculate the exact v2 structural revision while retaining explicit v1 migration support.
- `scripts/lib/conversations/withArchiveWriteLock.ts` — take its lock path from the state directory and keep correctness in revision comparison, not lock presence.
- `scripts/lib/conversations/ConversationCaptureStore.ts` — expose sorted distinct fragments for append preparation; it remains temporary and native SQLite.
- `scripts/lib/conversations/mergeConversationRecordFragments.ts` — document compatibility-only pair merge and delegate journal materialization to the set reducer.
- `scripts/lib/conversations/loadConversationExportStore.ts` — preserve full fragment identity rather than treating a merged store row as an authoritative latest revision.
- `scripts/lib/conversations/streamConversationExport.ts` — expose exact record bytes needed for lossless migration validation.
- `scripts/commands/conversationsImport.ts` — accept v2 archive directory and render revision-refusal/retry details.
- `scripts/commands/conversationsExport.ts` — remain a complete portable export; do not use it in the scheduled v2 path.

The legacy `writeConversationExportFromStore.ts`, `backupConversationArchive.ts`, `types/ConversationExportManifest.ts`, and v1 parser remain unchanged for portable export, rollback, and migration.

### 9.3 Rocket Agents tests

- `CONVERSATION_ARCHIVE_BATCH_TEST.ts` — canonical line bytes, checksum coverage, filename binding, fsync publication ordering, and rejection of extra or torn bytes.
- `CONVERSATION_ARCHIVE_REVISION_TEST.ts` — revision changes for each append, stale local publication refuses, and multiple writer batches union deterministically.
- `CONVERSATION_ARCHIVE_MATERIALIZATION_TEST.ts` — every permutation and duplicate of fragments yields identical bytes; 353/356-event branches yield all events.
- `CONVERSATION_CAPTURE_INCREMENTAL_TEST.ts` — unchanged hit, append resume, prefix rewrite, same-size/restored-mtime rewrite, atomic replacement, truncation, WAL-only change, mutation-during-read retry, cache-loss fallback, archive-ID mismatch, same-ID reseed missing a fragment, stale archive index, and tombstone-barrier presence.
- `CONVERSATION_EVENT_VARIANT_TEST.ts` — unresolved variants remain retained/order-independent; a reviewed choice survives compaction and a stale-normalizer append; unseen variants diagnose; concurrent and superseding resolutions converge.
- `CONVERSATION_ARCHIVE_PEER_MEMBERSHIP_TEST.ts` — aliases collapse by writer identity, unseeded targets never enroll, retirement is observed-remove, and returning retired writers are refused.
- `CONVERSATION_ARCHIVE_TOMBSTONE_TEST.ts` — observed fragments are removed, unseen concurrent fragments survive, and stale fragments do not resurrect after compaction.
- `CONVERSATION_TOMBSTONE_POLICY_TEST.ts` — missing/evicted source artifacts emit no tombstone; only explicit apply commands do.
- `CONVERSATION_WRITER_IDENTITY_TEST.ts` — missing non-empty identity refuses, peer duplicate refuses, and explicit rotation preserves old frontier.
- `CONVERSATION_ARCHIVE_COMPACTION_TEST.ts` — snapshot state equals pre-compaction state, stale CAS refuses, old readers finish, resolutions/membership survive, and covered batches obey the 24-hour minimum plus 30-day no-ack ceiling.
- `CONVERSATION_ARCHIVE_RECOVERY_TEST.ts` — `.tmp` tails are ignored, final corruption stops, and a deleted derived index rebuilds exactly.
- `CONVERSATION_ARCHIVE_MIGRATION_TEST.ts` — v1 count, IDs, event IDs, event bytes, metadata, and original fragment provenance equal the initial v2 snapshot; it also proves that the deliberately reformulated v2 union provenance and state hash are not used as cross-format equality criteria.
- `CONVERSATION_ARCHIVE_SYNC_TEST.ts` — multi-peer append, append/compact, alias identity, never-held target, absent/retired peer, daily drift, clock-skew, interruption, stale peer, collision, and divergent-compaction matrix.
- Existing `CONVERSATION_ARCHIVE_CONCURRENCY_TEST.ts` — retarget lost-update and divergent-revision cases to v2 without weakening assertions.
- Fixtures under `scripts/lib/conversations/fixtures/archive-v2/` — byte-exact valid/corrupt batches, snapshots, tombstones, divergent fragments, resolutions, peer membership, and Python parity vectors.

### 9.4 Atrium: new files

Each Python module exposes one public unit.

- `atrium/ingest/archive_cursor.py` — immutable cursor value type.
- `atrium/ingest/read_archive_head.py` — validate format/head and enumerate immutable inputs.
- `atrium/ingest/read_archive_batch.py` — validate and stream one batch with byte offsets.
- `atrium/ingest/read_archive_snapshot.py` — validate and stream normalized snapshot state.
- `atrium/ingest/materialize_archive_conversation.py` — Python implementation of the set reducer.
- `atrium/ingest/archive_event_conflict.py` — derived conversation-scoped event-variant diagnostic.
- `atrium/ingest/select_archive_event_variant.py` — apply durable resolution/fallback semantics from shared fixtures.
- `atrium/ingest/apply_archive_entry.py` — idempotently update derived fragment/event state.
- `atrium/ingest/load_archive_cursor.py` — read cursor tables.
- `atrium/ingest/save_archive_cursor.py` — persist cursor in the caller's transaction.
- `atrium/ingest/ingest_archive_increment.py` — bounded journal transactions.
- `atrium/ingest/reconcile_archive_snapshot.py` — all-or-nothing full snapshot pass and absent-conversation sweep.
- `atrium/store/archive_state_schema.py` — disposable cursor, fragment, event-origin, and state tables.

### 9.5 Atrium: changed files

- `atrium/ingest/read_archive.py` — become a compatibility facade that yields materialized records from v1 or a stable v2 head; parsing lives in the single-purpose modules above.
- `atrium/cli.py` — delegate `ingest` to the new orchestrators, add `--rebuild-archive-state`, and remove the current inline `_ingest` implementation.
- `atrium/store/schema.py` — include the derived archive-state schema and its build-version stamp.
- `atrium/store/write_conversation.py` — no semantic change; continue exact replacement and unchanged detection.
- `atrium/store/delete_absent_conversations.py` — no semantic change; call only from validated full snapshot reconciliation.

### 9.6 Atrium tests

- `tests/test_archive_v2_reader.py` — exact fixture parsing, checksum failures, gaps, collisions, and temporary-tail handling.
- `tests/test_archive_incremental_ingest.py` — bounded transactions, same-transaction cursor updates, crash replay, and per-writer progress.
- `tests/test_archive_materialization_parity.py` — consume Rocket Agents parity fixtures and assert identical record bytes/hashes for every permutation.
- `tests/test_archive_event_conflicts.py` — retain variants, honor/supersede resolutions on every order, report unresolved/unseen conflicts, and continue unrelated ingestion.
- `tests/test_archive_compaction_reconcile.py` — snapshot change invalidates cursor, full sweep removes absent records, and failure rolls back all changes.
- Existing `tests/test_ingest.py` — retain v1 compatibility cases and add the v2 facade path.
- Existing index-consistency tests — assert unchanged conversations retain vectors after incremental journal ingest.

### 9.7 Dotfiles: new and changed files

- `bin/sync-conversations` (changed) — replace full archive exchange with validated inventory, missing immutable-object transfer, head reconciliation, semantic comparison, and freeze-sentinel refusal.
- `bin/sync-all-safe` (changed) — keep the 14:00 route order, report a machine-readable per-route outcome, identify aliases through peer info, and distinguish unreachable/not-enrolled from failed archive sync.
- `bin/conversation-writers` (new) — freeze, verify-frozen, clear a proved-stale orchestrator lock, and verify-running for the actual LaunchAgents and SessionEnd guard.
- `bin/atrium-refresh` (new, canonicalizing the currently installed but unversioned runtime script) — direct v2 capture/append, incremental Atrium ingest, threshold compaction request, synthesis ingest, and embed.
- `launchd/com.cristian.atrium-refresh.plist` (new, canonicalizing the installed plist) — version the hourly guarded refresh configuration.
- `claude/hooks/atrium-refresh-on-session-end.sh` (changed) — exit when `migration.freeze` exists before detaching the guarded refresh.
- `launchd/com.cristian.sync-all-safe.plist` (changed) — retain the installed daily schedule and make it the sole conversation-transport LaunchAgent.
- `launchd/com.cristian.sync-conversations.plist` (deleted) — remove the uninstalled legacy schedule so migration tooling and operators cannot mistake it for a live writer.
- `scripts/test-conversation-sync` (changed) — fixture-driven object transfer, alias/peer identity, freeze discovery, cache reseed, and complete failure matrix.
- `scripts/check-conversation-ownership` (changed) — enforce that dotfiles transports objects but contains no merge or archive parsing policy.

## 10. Measurement plan

### 10.1 Existing baseline

The supplied benchmark began with 27,041 records and a 3,423,794,309-byte v1 archive. Adding one 680-byte input conversation produced 27,042 records and a 3,423,794,792-byte archive in 132.36 seconds real time with 563,314,688 bytes maximum resident set size. The importer read the 3,423,794,309-byte source, copied a 3,423,794,309-byte full backup, and wrote the 3,423,794,792-byte replacement: at least 10,271,383,410 bytes (10.27 GB decimal) of archive-file I/O before temporary SQLite and filesystem overhead. Preserve `bench/baseline-import.log`, both measured archive files, the input, and their hashes as baseline evidence.

Capture is a separate and larger measured O(corpus) term. A live `run-conversations-export.ts --allow-partial` pass took 226.91 seconds real, 106.27 seconds user, and 28.65 seconds system; reached 1,634,369,536 bytes maximum resident set size; and wrote a 2,780,392,214-byte slice containing 23,606 conversations. V2 must eliminate both the full capture slice and the full publish rewrite.

The current operational cadence is not simply hourly. The installed LaunchAgent has a 3,600-second interval, but the SessionEnd hook also invokes the same refresh and the script accepts it after `MIN_INTERVAL=900`. During active use this produces a new start roughly one completed-run duration plus 15 minutes after the prior completion—observed start gaps around 20–35 minutes—with full runs taking roughly 4.0–8.5 minutes. For example, the live log's 19:37:51 run finished at 19:46:18 (8 minutes 27 seconds). The review's quoted `duplicates: 23580, added: 4, updated: 14` belongs to that 19:37 run and sums to 23,598 input conversations, not 23,584 and not the 17:43 run. The 17:43:15 run exported 23,588 and imported 5 added, 23,575 duplicate, and 8 updated records in 5 minutes 3 seconds. The correction does not weaken the finding: both runs reprocessed roughly 23.6 thousand artifacts to publish a handful of changes.

Conversation transport has a different cadence: the installed `com.cristian.sync-all-safe` runs at 14:00 daily, while capture can advance every 15 minutes after a completed refresh. Measure archive parity only as a sync-then-dry event, and record the last successful sync separately from schedule presence. At the Round 3 inspection, `com.cristian.sync-conversations` was not installed and a stale `sync-all-safe.lock` made the daily job skip its entire heavy-sync section; this is evidence that configured cadence is not executed cadence. The same inspection verified the local v1 manifest at 27,070 records with `contentSha256` `53c80bba63839af8343be7e78b2c04d31c9f0d05ef4cfb9789fd59faea49fc9d`. A remote manifest must be freshly probed during migration; this review environment could not independently open the SSH connection.

### 10.2 Controlled benchmark corpus

Run all benchmarks on copies under a timestamped state-directory benchmark root, never on the live archive. Record hardware, OS, Node, filesystem, git SHA, archive byte size, record count, and source hash:

```bash
BENCH="$HOME/.local/state/rocket-agents/conversations/bench/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BENCH"
system_profiler SPHardwareDataType > "$BENCH/hardware.txt"
sw_vers > "$BENCH/os.txt"
node --version > "$BENCH/node.txt"
git -C "$HOME/p/rocket-agents" rev-parse HEAD > "$BENCH/git-sha.txt"
stat -f '%z' "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" > "$BENCH/v1.bytes"
shasum -a 256 "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" > "$BENCH/v1.sha256"
```

`conversations:benchmark-fixtures` must deterministically produce append sets of 1, 10, 100, and 1,000 new conversations and an update fixture with the 353/356-event divergent record.

### 10.3 Capture scaling

Build fixture source trees with 1,000, 10,000, and 25,000 unchanged artifacts, then apply identical change sets of 0, 1, 10, and 100 artifacts. For each corpus, measure: cold cache; warm no-op; one JSONL append; one same-size in-place rewrite with mtime restored; and cache deletion followed by recovery. The benchmark command writes metrics JSON and `/usr/bin/time -l` output:

```bash
pnpm run conversations:benchmark-capture-fixtures -- \
  --output "$BENCH/capture-fixtures" --artifacts 25000 --changed 1
/usr/bin/time -l pnpm run conversations:capture -- \
  --home "$BENCH/capture-fixtures/home" \
  --append-to "$BENCH/archive-v2" \
  --capture-index "$BENCH/capture-index.sqlite3" \
  --metrics "$BENCH/capture-25000-1.json" \
  > "$BENCH/capture-25000-1.out" 2> "$BENCH/capture-25000-1.time"
```

Release evidence must show:

- warm no-op: every artifact is a fingerprint cache hit, `payloadBytesRead=0`, `recordsNormalized=0`, `fragmentsAppended=0`, and no batch or export slice is written;
- changed runs: `fullyParsed + tailResumed` equals the changed-artifact count, unchanged artifacts contribute no payload reads, and JSONL prefix lines are not parsed again;
- same-size/restored-mtime rewrite: `ctimeNs` invalidates the row and the semantic result matches a cold full pass;
- cache deletion and normalizer-version change: a full pass occurs and its semantic inventory exactly matches the warm-cache result;
- replacing/reseeding the archive while retaining `capture-index.sqlite3`: archive-ID mismatch or missing-fragment presence causes per-artifact full capture, never a hit; the result matches a cold pass;
- with one identical changed artifact, increasing 1,000 to 25,000 unchanged artifacts increases only discovery/fstat metrics, not parsed records, redactions, payload bytes, or journal bytes;
- 1, 10, and 100 changed-artifact trials report work and bytes proportional to their changed inputs; and
- on the live-scale 25,000-artifact fixture, one changed artifact has p50 real time no more than 10% of the measured 226.91-second full export and peak RSS below one third of the measured 1,634,369,536 bytes.

Report metadata-enumeration time separately so the design does not mislabel an O(path-count) stat walk as O(1). The goal is that corpus-sized payload work disappears; cache recovery remains an explicit O(corpus) safety fallback.

### 10.4 Import scaling

For each `N`, start from the same verified migrated snapshot, clear only disposable state, and run five trials. Capture `/usr/bin/time -l`, journal bytes before/after, new object count, and semantic verification:

```bash
/usr/bin/time -l pnpm run conversations:import -- \
  --input "$BENCH/fixtures/n-0001.jsonl" \
  --archive "$BENCH/archive-v2" --apply \
  > "$BENCH/n-0001.out" 2> "$BENCH/n-0001.time"
du -sk "$BENCH/archive-v2/journal" > "$BENCH/n-0001.journal-kib"
pnpm run conversations:verify-v2 -- --archive "$BENCH/archive-v2" --deep \
  > "$BENCH/n-0001.verify"
```

Repeat with the four fixture sizes and retain individual trials rather than only an average. Report p50 and maximum real time, user time, system time, maximum resident set, bytes written, and bytes per appended input byte. Acceptance is:

- no full snapshot or legacy archive file changes during an append;
- journal byte growth within 10% of batch header/footer plus canonical entry bytes;
- 1-conversation p50 at least 20 times faster than the 132.36-second baseline on the same machine;
- doubling `N` does not cause superlinear bytes written; and
- every trial passes semantic verification.

### 10.5 Atrium incremental cost

Copy the same initial Atrium index for each fixture size. Measure `uv run atrium ingest` with `/usr/bin/time -l`, record cursor before/after, SQLite page count/freelist count, changed conversation count, and search availability. Acceptance is that no full sweep is logged when snapshot identity is unchanged and only fixture conversation IDs are rewritten.

After a forced compaction, measure one explicit full reconciliation separately. It is not included in incremental latency claims.

Before migration cutover, measure the deliberate provenance-induced rewrite on a production-index copy and prove semantic vectors are untouched:

```bash
cp -p "$HOME/.atrium/index.sqlite3" "$BENCH/atrium-cutover.sqlite3"
sqlite3 "$BENCH/atrium-cutover.sqlite3" \
  "select count(*) from records where role not in ('note','synthesis'); select count(*) from vectors;" \
  > "$BENCH/atrium-cutover.before"
/usr/bin/time -l uv run atrium --index "$BENCH/atrium-cutover.sqlite3" \
  ingest "$BENCH/archive-v2" \
  > "$BENCH/atrium-cutover.out" 2> "$BENCH/atrium-cutover.time"
sqlite3 "$BENCH/atrium-cutover.sqlite3" \
  "select count(*) from records where role not in ('note','synthesis'); select count(*) from vectors; pragma page_count; pragma freelist_count;" \
  > "$BENCH/atrium-cutover.after"
```

The raw-row count and FTS consistency must match a clean rebuild, and the vector count plus a sorted `(record_id, length(vector))` digest must be identical before and after. Record elapsed time, maximum RSS, database/WAL peak bytes, and minimum free space. Do not budget an all-raw-record embedding run; current source does not perform one.

### 10.6 Sync transfer cost

The sync command writes a JSON report containing inventory bytes, missing object count, missing object bytes, rsync sent/received bytes, reconciliation mode, and semantic digests. Measure:

1. fully converged dry run;
2. one new small batch on one host;
3. simultaneous batches on three enrolled peers;
4. one forced compaction plus one remote append; and
5. interrupted snapshot transfer followed by resume;
6. `portatil-usb` and `portatil` resolving to one writer identity;
7. a configured never-enrolled target; and
8. an enrolled peer returning after the 30-day no-ack ceiling.

Acceptance is zero payload bytes on an immediate post-sync dry run apart from inventories, approximately the new batch size for case 2, the sum of all peer batches for case 3, one snapshot plus the remote batch for case 4, one acknowledgement for the two routes in case 6, no enrollment or canonical transfer in case 7, a validated full-snapshot reseed in case 8, and identical final digests in every completed sync. The 3.4 GB v1 file must never appear in an rsync file list after cutover.

### 10.7 Verification commands for the implementation

The implementation is not releasable until these commands pass from the repository roots:

```bash
cd "$HOME/p/rocket-agents" && ./scripts/check
cd "$HOME/p/atrium" && uv run ruff check . && uv run ruff format --check . && uv run pytest tests/ -q
cd "$HOME/p/dotfiles" && ./scripts/check
```

Then run the migration equivalence, v2 deep verification, sync-plus-dry acceptance, and benchmark commands above. A green unit suite without the live-corpus semantic comparison is insufficient.

## 11. Rejected alternatives and changed recommendations

### Round 2: incremental capture is required

Changed. Direct `--append-to` publication alone still left `captureConversationArtifacts` reparsing every provider artifact. Section 4.3 now makes a disposable fingerprint/checkpoint cache part of v2, specifies append-tail and rewrite detection, and requires separate capture scaling measurements. The cache may fall back to a full pass but may never turn loss into a cache hit.

### Round 2: v1 and v2 record hashes are not equal

Changed. The migration no longer requires full record-hash or v1/v2 state-hash equality, because v2 deliberately derives union provenance differently. It proves exact ID, event ID, event bytes, metadata, and original fragment-provenance preservation instead. The first v2 Atrium pass is explicitly budgeted as a raw-row/FTS rewrite. The claim that it re-embeds all raw rows is rejected: current `semantic_roles.py` limits vectors to `note` and `synthesis`, while raw conversations remain lexical-only.

### Round 2: event conflicts are scoped and deterministic

Changed. A duplicate event ID with different bytes no longer stops the archive. The archive retains every variant, unresolved materialization uses a deterministic byte tie-break, diagnostics name the affected conversation, and unrelated capture/ingestion continues. Round 3 adds the durable reviewed resolution that the tie-break lacked. This matches the verified current ID formula, which excludes kind, role, and timestamp.

### Round 2: snapshots do not duplicate materialized records

Changed. The inline `record` and `recordSha256` were removed from live snapshot state. Readers rebuild once from normalized fragments and event variants and cache the result; this avoids repeating every event body in the corpus-sized transfer object.

### Round 2: tombstones have explicit producers

Changed. Section 2.8 now assigns tombstone creation only to previewed Rocket Agents delete, redact, repair, and conflict-resolution commands. Capture absence, cache eviction, provider sweeps, schedulers, and Atrium can never infer deletion, protecting archive-only conversations.

### Round 2: writer identity is durable

Changed. `writer-id` was removed from disposable state and replaced by host-local durable `local-writer.json` under the data directory. Missing identity stops publication; rotation is explicit; old frontier entries remain as permanent causal barriers in v2.

### Round 2: measured baseline and cadence

Changed and corrected. Section 10.1 now records the 27,041-record pre-import size, at least 10.27 GB of archive-file I/O for one addition, the independent 226.91-second/2.78-GB capture pass, and the SessionEnd-plus-15-minute-floor duty cycle. The review associated one log tuple with the wrong run and misstated its total: `23580 + 4 + 14` is 23,598 at 19:37, while the 17:43 run was 23,588 with `23575 + 5 + 8`. The architectural conclusion remains unchanged.

### Round 3: peer topology, acknowledgement, and scheduler freeze

Changed. Sections 5.3, 7, and 8 now distinguish configured routes from enrolled archive peers, key identity and acknowledgement by `(archiveId, writerId)`, collapse the two `portatil` routes, exclude never-held targets, preserve a 24-hour minimum plus 30-day no-ack ceiling, and specify explicit peer retirement/full-snapshot return. Migration inventories all routes but must cover every distinct archive holder; an unreachable holder blocks lossless cutover. Freeze now targets the installed `com.cristian.sync-all-safe` and `com.cristian.atrium-refresh` agents plus the SessionEnd sentinel guard, and verifies all known labels/locks by name.

One operational phrase in the review is rejected as written. The source does make `neo` a daily configured target and would log `! sync VPS failed` after a reachable transport failure, but the local log shows the 2026-08-20 peer attempt failed on a remote sync lock and later scheduled runs did not reach `neo` or any other peer: a stale local `sync-all-safe.lock` made them report `another sync is running, skipping heavy sync`. The script also emits explicit `not reachable, skipped` and failure lines rather than skipping silently. The topology defect is accepted; the evidence says daily convergence is currently absent, not that `neo` is actually attempted and fails on every daily run. Remote checkout/disk claims remain migration-preflight probes rather than timeless design assumptions.

### Round 3: convergence is an acceptance window

Changed. A non-zero dry plan before freeze is normal drift because capture is more frequent than the daily orchestrator. Section 8.2 establishes v1 parity only after all writers are frozen, with provider-free pairwise sync followed by two complete zero-dry cycles across every distinct archive peer. The supplied local manifest was independently reproduced; the remote manifest could not be reopened from this restricted review environment, so current remote equality or inequality is not asserted beyond the dated evidence in `ROUND3.md`.

### Round 3: capture cache is bound to canonical evidence

Changed. Every artifact row carries the archive ID, and an unchanged fingerprint is insufficient for a hit. A capture hit now requires exact-revision `archive-index.sqlite3` evidence that every cached fragment hash is active or has a tombstone barrier in the current head. Archive replacement, rollback quarantine, migration, or same-ID reseeding with missing fragments forces a full pass for the affected artifact. Presence checks are indexed by fragment hash and proportional to that artifact's cached fragments.

### Round 3: event-variant repair is durable

Changed. Lowest canonical bytes remains only the unresolved availability fallback. Section 2.9 adds a journaled operator resolution with observed variants and superseded-resolution hashes; snapshots retain it, concurrent choices remain deterministic/diagnosed, and a stale normalizer reintroducing an old fragment cannot displace the reviewed choice. The alternative claim that a normalizer change necessarily changes the event ID is rejected by source: `conversationEventFromRecord.ts` hashes only record index and redacted text, while the three kind/role/timestamp derivation functions do not feed `hashText`.

### One mutable append file

Rejected. A local append is cheap, but installations that append different bytes at the same offset create divergent tails that rsync cannot union safely. Compaction replacing that file while a peer appends adds another destructive race. Immutable transaction segments retain one logical journal without a shared-tail conflict.

### Partitioning by source or period

Rejected as before. It moves merge and compaction complexity into partition boundaries, makes a cross-source conversation policy harder, and does not solve concurrent replacement. Batch segmentation is transaction atomicity, not domain or time partitioning.

### `id -> latest revision/hash/offset`

Rejected and explicitly changed from the earlier shorthand. Neither host's latest revision supersedes the other. The derived index stores fragment sets, tombstone sets, event origins, and a materialized hash. The 353-event and 356-event fragments both contribute to the result.

### Folding the current pairwise merge function over journal order

Rejected. The function is commutative for a pair, but its nested provenance hash and selected metadata make arbitrary grouping unsafe. A set reducer over all distinct fragments is associative and idempotent.

### Last-writer-wins by timestamp, mtime, or host

Rejected. Clock skew and deleted source rollouts make recency neither trustworthy nor a statement of authority. It would reproduce the known three-event loss.

### Lock-only correctness

Rejected. Locks reduce contention but can be bypassed, stale, or scoped incorrectly. Every replacement operation uses a revision compare-and-swap; append publication uses exclusive immutable filenames.

### Raw byte offset as the Atrium cursor

Rejected and changed from the earlier shorthand. A byte offset has no meaning after compaction and cannot represent multiple independent writers. The cursor is snapshot identity plus per-writer sequence/hash and an optional within-batch byte offset.

### Immediate deletion of compacted batches

Rejected. Covered objects remain for at least 24 hours. After that minimum, complete acknowledgement permits pruning; after 30 days, a deeply validated current snapshot plus the retained previous snapshot permits pruning without an absent peer and makes that peer pay for a full reseed. Lost acknowledgement or retention state delays pruning but cannot accelerate it.

### Delete-wins tombstones or timestamp tombstones

Rejected. A stale host could erase an unseen concurrent fragment. Observed-remove tombstones enumerate fragment hashes and make intentional deletion precise and replay-order independent.

### Canonical SQLite archive

Rejected. Although Node has native SQLite, syncing a live mutable database recreates whole-file transport, WAL/sidecar, and compaction coordination problems. SQLite remains appropriate only for disposable local indexes.

### Making Atrium's index or cursor canonical

Rejected. It violates the layer boundary and makes a deleted Atrium database a data-loss event. All fragments, tombstones, lineages, and checkpoints required for rebuild live under Rocket Agents data.

### Full snapshot on every refresh

Rejected. That is the current O(corpus) write amplification under another name. Snapshots are threshold-triggered checkpoints; normal refresh appends one batch and incrementally advances Atrium.

### Round 3: closure status

Closed at specification level:

- Item 1: route topology, identity-based enrollment/acknowledgement, bounded pruning, actual scheduler freeze, required migration peer discovery, and unreachable-peer refusal are specified.
- Item 2: convergence is defined as a frozen or post-sync acceptance window, not a steady state; multi-peer cycles replace the single `macmini` assumption.
- Item 3: capture-cache hits are bound to archive ID and exact-head fragment-presence evidence from the archive index.
- Item 4: reviewed event selection is a durable, compactable, supersedable journal operation that survives stale-normalizer appends.

Still open outside this design artifact:

- The implementation and all tests/benchmarks in sections 9 and 10 remain to be written and run.
- Migration cannot start until live SSH peer inventory succeeds for every configured route and every archive holder is reachable or recovered from a verified backup. This review independently reached only local files because its execution sandbox denied outbound SSH; it therefore does not certify the current remote manifests, `neo` disk state, or remote checkout state.
- The observed stale local `sync-all-safe.lock` must be diagnosed against live processes and cleared explicitly before using schedule health as convergence evidence.
- `neo` capacity/checkout remediation belongs to the sync-orchestrator operations backlog. Until it deliberately receives, validates, binds, and enrolls this archive, it is not an archive peer and cannot block pruning or migration.

## 12. Delivery verification

This specification is complete when the file exists, is non-empty, contains all required numbered subjects and Round 2/3 resolutions, contains no placeholder markers, and mentions every source file required by the briefing and Round 3 review. The command that verifies this document is:

```bash
test -s DESIGN.md && \
for heading in \
  'On-disk layout' 'Revision identity and concurrency' 'Merge and materialization semantics' \
  'Compaction' 'Atrium ingestion' 'Multi-installation sync' 'Lossless migration and rollback' \
  'File-by-file implementation plan' 'Measurement plan' 'Rejected alternatives' \
  'Incremental source capture' 'Round 2: incremental capture is required' \
  'Round 2: v1 and v2 record hashes are not equal' \
  'Round 2: event conflicts are scoped and deterministic' \
  'Round 2: snapshots do not duplicate materialized records' \
  'Round 2: tombstones have explicit producers' \
  'Round 2: writer identity is durable' \
  'Round 2: measured baseline and cadence' \
  'Round 3: peer topology, acknowledgement, and scheduler freeze' \
  'Round 3: convergence is an acceptance window' \
  'Round 3: capture cache is bound to canonical evidence' \
  'Round 3: event-variant repair is durable' \
  'Round 3: closure status'; do \
  grep -Fq "$heading" DESIGN.md || exit 1
done && \
for source in \
  'importConversationExport.ts' 'writeConversationExportFromStore.ts' \
  'ConversationCaptureStore.ts' 'mergeConversationRecordFragments.ts' \
  'readArchiveRevision.ts' 'withArchiveWriteLock.ts' \
  'loadConversationExportStore.ts' 'streamConversationExport.ts' \
  'exportConversations.ts' 'backupConversationArchive.ts' \
  'ConversationRecord.ts' 'ConversationExportManifest.ts' \
  'read_archive.py' 'cli.py' 'sync-conversations'; do \
  grep -Fq "$source" DESIGN.md || exit 1
done && \
for round3_source in \
  'sync-all-safe' 'com.cristian.sync-all-safe.plist' \
  'com.cristian.sync-conversations.plist' 'com.cristian.atrium-refresh.plist' \
  'atrium-refresh-on-session-end.sh' 'conversationEventFromRecord.ts' \
  'conversationEventKindFromRecord.ts' 'conversationRoleFromRecord.ts' \
  'conversationTimestampFromRecord.ts'; do \
  grep -Fq "$round3_source" DESIGN.md || exit 1
done && \
grep -Fq 'eventVariants' DESIGN.md && \
grep -Fq 'conversations:tombstone' DESIGN.md && \
grep -Fq 'local-writer.json' DESIGN.md && \
grep -Fq '10,271,383,410' DESIGN.md && \
grep -Fq 'SEMANTIC_ROLES' DESIGN.md && \
grep -Fq 'conversation-event-variant-resolution' DESIGN.md && \
grep -Fq 'archive-peer-enrollment' DESIGN.md && \
grep -Fq 'hasPublishedConversationFragments' DESIGN.md && \
grep -Fq 'com.cristian.sync-all-safe' DESIGN.md && \
grep -Fq '30-day no-ack ceiling' DESIGN.md && \
test "$(grep -c '^### Round 2:' DESIGN.md)" -eq 7 && \
test "$(grep -c '^### Round 3:' DESIGN.md)" -eq 5 && \
test "$(( $(grep -c '^```' DESIGN.md) % 2 ))" -eq 0 && \
if sed '/^## 12\./,$d' DESIGN.md | \
  grep -Eq 'TODO|TBD|PLACEHOLDER|require-record-hash-equality|initial snapshot state hash must also equal'; then
  exit 1
fi
```

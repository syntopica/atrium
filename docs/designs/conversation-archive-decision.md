# Decision: immutable segments with sealed-generation erasure

## The call

Choose **F with a named erasure mechanism: sealed-generation replacement**.
Do not implement the full option C journal, tombstone, snapshot, frontier,
writer-identity, peer-membership, and acknowledgement protocol.

Normal capture publishes immutable, content-addressed segments. A no-op capture
publishes nothing. Synchronization unions missing segments only when both sides
name the same generation. Rocket Agents materializes the set of distinct
fragments with one commutative, associative, and idempotent reducer. One
disposable SQLite database holds the segment inventory, materialized records,
artifact fingerprints, and pending Atrium deliveries. Atrium consumes full
exports for rebuilds and `atrium ingest --partial` slices for increments; it
does not own a second reducer.

Deletion and corrective redaction are rare, explicit, offline operations. They
replace the complete generation:

1. `conversations:erase` creates a reviewable plan bound to the exact current
   generation and segment-set digest. The plan names the conversations,
   fragments, event variants, and intended replacements or removals.
2. With capture, sync, hourly refresh, and the SessionEnd hook frozen, Rocket
   Agents materializes the generation once, applies only the reviewed plan,
   re-runs the current redactor where requested, and writes one sanitized base
   segment into a new generation directory. It copies no old segment into that
   generation.
3. The generation ID is derived from the validated base-segment hash. Every
   later segment header binds itself to that generation ID. A small
   `current-generation.json` reference selects the generation; normal sync
   refuses a generation mismatch and never unions an old-generation segment
   into a new generation.
4. The new generation is seeded and deep-validated on every known archive
   holder before any pointer changes. Pointers are then switched while writers
   remain frozen. A peer returning with the old generation is refused and must
   be explicitly reseeded.
5. After semantic comparison and a recovery decision, all managed copies of
   the old generation and affected backups are removed explicitly. Credential
   revocation happens before that purge. SSD deletion cannot prove physical
   media erasure, and no protocol can erase an unknown or unreachable copy;
   this mechanism guarantees logical removal from every inventoried managed
   copy.

The durable shape is deliberately small:

```text
segments/
  current-generation.json
  generations/
    g_<generation-id>/
      generation.json
      segments/
        s_<segment-sha256>.jsonl
```

This is enough because erasure itself already requires a corpus rewrite to
remove the offending bytes from immutable files. Option C's tombstone can hide
the fragment immediately, but the bytes remain in the old batch until
compaction and peer-safe pruning. The sealed-generation operation performs the
rewrite directly and uses generation mismatch as the anti-resurrection
barrier. It pays corpus-scale work only when erasure is explicitly invoked,
not on every capture and sync.

The mechanism adds seven named files beyond option F:

- `scripts/lib/conversations/types/ConversationErasurePlan.ts`
- `scripts/lib/conversations/planConversationArchiveErasure.ts`
- `scripts/lib/conversations/applyConversationArchiveErasure.ts`
- `scripts/lib/conversations/verifyConversationArchiveErasure.ts`
- `scripts/commands/conversationsErase.ts`
- `scripts/bin/run-conversations-erase.ts`
- `scripts/lib/conversations/CONVERSATION_ARCHIVE_ERASURE_TEST.ts`

It also changes `package.json`, the shared generation validator, and
`sync-conversations`. Starting from option F's current 37-45 new-or-changed-file
estimate, the decision costs about 44-52 new or changed files. That is still
material, but it is far below `DESIGN.md`'s 116 named new files plus its changed
files. The generation boundary is not optional: without it, a stale `peer-c`
or `peer-a` could reintroduce erased segments after an offline rewrite.

## Evidence checked against the current source and data

- Rocket Agents really redacts during normalization. `conversationEventFromRecord.ts`
  calls `redactSensitiveText.ts`; that function composes
  `redactPrivateKeyBlocks.ts`, `redactAssignedSecrets.ts`, and
  `applyRedactionPattern.ts`. `redactConversationHome.ts` separately removes
  the local home path. `ConversationProvenance.redactions` is a required number.
- Redaction is corpus-scale, not hypothetical. A binary LF-only validation of
  the live archive found 30,740 valid records, of which 4,037 carry at least one
  redaction; their recorded total is 104,838 redactions, or 13.13% of records.
- The schema premise in `DECIDE.md` is already stale. The live manifest now
  reports 30,740 records at schema 2, its content hash matches its payload, and
  every record is schema 2. The retained 30,728-record backup is also valid but
  contains 27,889 schema-1 and 2,839 schema-2 records. Commit `5560479` upgraded
  records at serialization, and a full write has now crossed that boundary.
  The segment migration must still call the idempotent
  `upgradeConversationRecord`, but it must not assume that another schema
  rewrite is pending.
- `importConversationExport.ts` loads the complete existing archive, merges the
  complete input, takes a full backup, and rewrites the complete archive under
  a revision check. `backupConversationArchive.ts` copies the whole file.
  `writeConversationExportFromStore.ts` streams the whole store to a replacement
  file. The measured write amplification therefore follows directly from code.
- Capture has no persistent cache. `captureConversations.ts` starts with an
  empty map, and `captureConversationArtifacts.ts` visits every discovered
  artifact and calls `captureConversationArtifact`. Segment publication alone
  would not remove the 226.91-second full capture pass.
- The current pair merge is not a set reducer. It orders two records by
  provenance hash, overwrites equal event IDs from the right side, and hashes
  the two provenance hashes. It is pairwise commutative but grouping-dependent.
  A reducer over the complete distinct fragment set remains mandatory.
- Atrium already has the required synthesis re-key and backup behavior.
  `rekey_synthesis_registry.py` is idempotent, refuses divergent destination
  collisions, and calls `backup_synthesis_records.py` before its first write.
  The focused suite passed: 8 tests. During this review the plan changed from
  16,148 legacy plus 489 current records to 0 legacy, with 0 collisions;
  `records.bak-20260831T205029` contains 16,677 records. A later archive-aware
  repair dry run found 0 mis-stamped records and 16,704 records already agreeing
  with the archive. That external state moved while this document was being
  prepared, so the migration must re-inventory it under the freeze instead of
  replaying the old 16,148-record plan.
- Atrium's `--partial` behavior exists and is tested. `_ingest(..., sweep=False)`
  writes named conversations without `delete_absent_conversations`; a full
  ingest performs the provider-scoped absence sweep. Incremental segment
  delivery can therefore remain a Rocket Agents export slice.
- The real local schedulers are `com.cristian.sync-all-safe` at 14:00 and
  `com.cristian.atrium-refresh` every 3,600 seconds. Both are loaded.
  `com.cristian.sync-conversations` is not loaded. The Claude SessionEnd hook
  invokes the same guarded refresh. Neither the installed refresh script nor
  the SessionEnd hook currently checks a migration freeze sentinel, so that
  guard must land before live migration.
- `sync-all-safe` addresses `peer-a`, one of `peer-c-usb` or `peer-c`, and
  `peer-b`. The two `peer-c` routes are one physical laptop. The latest
  retained `peer-a` sync evidence shows 10,134 records on `peer-a`, 30,728 locally
  after merging its contribution, and a failed attempt to send the full Mac
  archive back because `peer-a` ran out of disk. `peer-a` is therefore an archive
  holder and part of this migration, not an optional never-enrolled route.
- Live SSH inventory could not be repeated from this sandbox. The required
  peer set is this Mac, `peer-b`, `peer-c`, and `peer-a`; any one being
  unreachable or lacking enough free space stops the lossless cutover.

## What breaks if this call is wrong

| Wrong assumption                                                               | What breaks                                                                                                                                                                                                                                      | Recovery cost                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Erasure is needed but no tested mechanism exists                               | A missed credential remains in every immutable segment and sync multiplies it. The archive violates the instruction not to store credential values.                                                                                              | High and urgent: revoke the credential, invent a corpus rewrite under incident pressure, freeze every peer, and prove that old segments cannot return. This is why sealed-generation replacement is part of the first format.                                                                                                            |
| Erasure becomes frequent, must be online, or must proceed while peers write    | Each erasure rewrites and redistributes roughly the whole corpus. An unavailable `peer-c` blocks complete managed-copy removal; repeated freezes become operationally unacceptable.                                                            | Medium-high: retain the fragment and resolution schemas, add option C's observed-remove tombstones, writer sequences, frontiers, snapshots, acknowledgements, and pruning. Expect roughly 60-70 additional files and another coordinated migration. The existing segments remain reusable inputs, so this is not a data-format dead end. |
| The erasure plan names too much                                                | Archive-only conversations, including records with no surviving provider artifact, can be destroyed. Once every old generation and backup is purged, recovery may be impossible.                                                                 | Cheap before purge: switch the generation reference back while frozen. Impossible after purge unless a separately inventoried backup survives. Therefore plan/apply separation, per-ID/event semantic diff, and explicit purge approval are mandatory.                                                                                   |
| A stale peer is allowed to sync across generations                             | It can resurrect the exact bytes the erasure removed.                                                                                                                                                                                            | High: freeze again, rebuild another clean generation, reseed every peer, and repeat managed-copy purge. Normal sync must fail closed on generation mismatch.                                                                                                                                                                             |
| Source disappearance is treated as deletion                                    | The archive loses the records it exists to preserve; provider recapture cannot recover archive-only history.                                                                                                                                     | Potentially impossible. Source absence may delete only a disposable fingerprint row. It can never create an erasure plan or remove a fragment.                                                                                                                                                                                           |
| Full option C was actually unnecessary but implemented anyway                  | Correctness becomes distributed across writer identity, sequence allocation, five entry kinds, frontiers, compaction, peer membership, acknowledgements, pruning, and two reducers. A defect in tombstone or pruning logic can become data loss. | High and continuing: 116 named new files plus changed files must be maintained and tested forever; removing the protocol later requires another canonical migration.                                                                                                                                                                     |
| Option F's simple fingerprint cache does not remove the expensive capture term | Publication becomes cheap but a changed monolithic SQLite or large JSONL artifact still dominates refresh time.                                                                                                                                  | Low to medium: measure by storage kind, then add JSONL suffix checkpoints or a proven provider row cursor only for the offending adapter. This does not change the canonical segment format.                                                                                                                                             |

The asymmetric risk decides the question. Shipping bare F leaves no safe answer
to a demonstrated security need. Shipping C pays a large permanent correctness
tax for online deletion that no current producer performs. F plus a sealed
generation makes the security operation explicit, expensive, and testable
without making every ordinary append a distributed log operation.

## Measurements and acceptance thresholds

Preserve these baselines rather than replacing them with estimates:

- One-conversation v1 publish: 132.36 seconds. Directly accounted archive-file
  I/O is 10,271,383,410 bytes (3.42 GB read, 3.42 GB backup, 3.42 GB replacement),
  before temporary SQLite and filesystem overhead; the operational shorthand
  is roughly 12 GB total I/O.
- Full capture: 226.91 seconds, 2,780,392,214 output bytes, and
  1,634,369,536 bytes maximum RSS for 23,606 conversations.
- Archive at the start of this request: 30,728 records. Archive at the verified
  read during this decision: 30,740 records, 4,019,837,616 bytes, all schema 2,
  and a matching manifest content hash. The migration baseline is the value
  measured after writers freeze, not either hard-coded count.

The implementation is accepted only when measurements show:

- warm no-op capture: `payloadBytesRead=0`, `recordsNormalized=0`,
  `fragmentsAppended=0`, no segment written;
- one changed artifact on a 25,000-artifact fixture: p50 at most 22.691 seconds
  and peak RSS below 544,789,845 bytes;
- one-conversation publication: p50 at most 6.618 seconds, no base segment or
  legacy archive byte changes, and segment growth within 10% of exact entry
  plus header/footer bytes;
- increasing unchanged artifacts changes discovery/stat work only; payload
  reads, normalization, redactions, and segment bytes track changed artifacts;
- immediate post-sync dry run: zero missing segments, zero transfer payload
  beyond inventories, identical generation ID, segment-set digest,
  conversation-ID digest, event-set digest, and materialized-state digest on
  all four installations; and
- erasure drill: the new generation contains none of the targeted fragment or
  event hashes, every non-target semantic field is equal, an old-generation
  peer is refused, and explicit reseeding converges it without resurrection.

## Staged execution plan

Commands named below that do not exist today are part of the stage that
introduces them. They are acceptance interfaces, not claims about the current
CLI.

### Stage 1: prove the format, reducer, and generation barrier on fixtures

This is what to implement first. It uses only synthetic fixtures and temporary
directories created by the tests. It must not read or write the live archive,
the synthesis registry, Atrium's live index, schedulers, hooks, or peers.

Stage 1 creates exactly these files:

- `scripts/lib/conversations/types/ConversationArchiveGeneration.ts`
- `scripts/lib/conversations/types/ConversationArchiveGenerationReference.ts`
- `scripts/lib/conversations/types/ConversationSegmentHeader.ts`
- `scripts/lib/conversations/types/ConversationSegmentFooter.ts`
- `scripts/lib/conversations/types/ConversationFragmentEntry.ts`
- `scripts/lib/conversations/types/ConversationEventVariantResolutionEntry.ts`
- `scripts/lib/conversations/types/ConversationErasurePlan.ts`
- `scripts/lib/conversations/serializeCanonicalConversationRecord.ts`
- `scripts/lib/conversations/hashConversationFragment.ts`
- `scripts/lib/conversations/materializeConversationFragmentSet.ts`
- `scripts/lib/conversations/serializeConversationSegment.ts`
- `scripts/lib/conversations/validateConversationSegment.ts`
- `scripts/lib/conversations/deriveConversationArchiveGenerationId.ts`
- `scripts/lib/conversations/planConversationArchiveErasure.ts`
- `scripts/lib/conversations/CONVERSATION_SEGMENT_FORMAT_TEST.ts`
- `scripts/lib/conversations/CONVERSATION_FRAGMENT_SET_TEST.ts`
- `scripts/lib/conversations/CONVERSATION_ARCHIVE_ERASURE_TEST.ts`

Each production source file has one export and one responsibility. Stage 1 deliberately
does not add filesystem publication, SQLite state, capture, migration, sync,
CLI, or Atrium code. Its reducer tests must cover every permutation and
duplicate of F353/F356, same-event-ID byte variants, reviewed resolutions, and
generation mismatch. Its erasure test plans a new generation but does not
delete anything.

Verification:

```bash
cd "$HOME/p/agents" && \
pnpm run type-check && \
pnpm exec tsx --test \
  scripts/lib/conversations/CONVERSATION_SEGMENT_FORMAT_TEST.ts \
  scripts/lib/conversations/CONVERSATION_FRAGMENT_SET_TEST.ts \
  scripts/lib/conversations/CONVERSATION_ARCHIVE_ERASURE_TEST.ts && \
pnpm run lint
```

### Stage 2: build local publication and incremental capture on disposable data

Add validated temp-write, file-fsync, exclusive content-addressed publication,
directory-fsync, stable segment inventory, one disposable SQLite state store,
artifact fingerprints, pending Atrium delivery, migration/verification CLIs,
and metrics. Use synthetic 1,000/10,000/25,000-artifact trees and copies of the
benchmark corpus only. Do not point a command at the live archive.

Start with whole-artifact recapture on a fingerprint miss. Add JSONL suffix
resume or provider row cursors in this stage only if the per-storage-kind
measurement misses the 22.691-second one-change threshold.

Verification:

```bash
cd "$HOME/p/agents" && \
pnpm run conversations:test && \
pnpm run conversations:benchmark-segments -- \
  --artifacts 25000 \
  --changed 1 \
  --baseline-capture-seconds 226.91 \
  --baseline-import-seconds 132.36 \
  --max-capture-seconds 22.691 \
  --max-import-seconds 6.618 \
  --require-warm-noop \
  --require-proportional-bytes \
  --max-rss-bytes 544789845
```

Landed 2026-09-01 in `rocket-agents` `8cc2849`, 51 new files, all on disposable
data. `pnpm run check` passes for the whole repository and the conversations
suite is at 73 tests. The measured acceptance run, one process per pass:

| pass            | seconds | payload bytes read | fragments | peak RSS |
| --------------- | ------: | -----------------: | --------: | -------: |
| cold, 25,000    |   38.03 |         39,300,000 |    25,000 |   398 MB |
| warm no-op      |    1.91 |                  0 |         0 |   267 MB |
| one changed     |    1.72 |              2,096 |         1 |   261 MB |
| one new         |    1.59 |              1,608 |         1 |   265 MB |

That is 132x the measured v1 capture and 83x the measured v1 publish, against
bounds of 22.691 s and 6.618 s. Every segment present before a pass is
byte-identical after it, matched by hash.

Three things the implementation settled that the plan had left open:

- A base segment cannot carry the generation id that is derived from its own
  hash, so it carries a sentinel and `generation.json` names it. A base segment
  the generation does not name is refused, exactly like a segment from another
  generation.
- A capture flushes at 2,000 staged fragments rather than accumulating. Peak
  memory then follows the flush size instead of the corpus being seeded; the
  unbounded version measured 602 MB and a single 44 MB segment for 25,000
  artifacts.
- Resident memory never returns inside a process, so passes sharing one cannot
  be compared: a pass that read 1,608 bytes reported 574,898,176 bytes because
  the seeding pass before it had grown the heap. Each pass now runs in its own
  process, which is also what the hourly agent and the SessionEnd hook do.

JSONL suffix resume was not built. The per-storage-kind measurement clears the
22.691-second threshold by more than an order of magnitude with whole-artifact
recapture, and the plan makes the checkpoint machinery conditional on missing
it.

### Stage 3: complete erasure, transport, Atrium delivery, and freeze controls in test homes

Implement `conversations:erase` plan/apply/verify, generation-bound object
exchange, generation-mismatch refusal and explicit reseed, migration semantic
inventories, the `sync-conversations` frozen mode, and the scheduler/hook freeze
sentinel. Change the refresh pipeline to publish one segment and pass only the
pending materialized slice to `atrium ingest --partial`; retain full ingest for
rebuilds. Test four installations, both `peer-c` aliases, interruption, stale
peer return, no-op convergence, and an erasure generation replacement. All
tests use isolated homes.

Verification:

```bash
cd "$HOME/p/agents" && pnpm run check && \
cd "$HOME/p/atrium" && \
uv run ruff check . && \
uv run ruff format --check . && \
uv run pytest tests/ -q && \
cd "$HOME/p/dotfiles" && ./scripts/check
```

### Stage 4: read-only live preflight

This is the first stage that touches real data, and it is read-only. It writes
reports under migration state but does not modify canonical archives, synthesis
records, the live Atrium index, schedulers, or hooks. Deploy the already-tested
code first, then inventory this Mac, `peer-a`, `peer-b`, `peer-c-usb`, and
`peer-c`. The two laptop routes must return the same installation fingerprint.
All four physical installations must be reachable. `peer-a` must have enough free
space for its existing archive, an incoming base, transfer staging, and safety
margin; require at least three times the frozen archive bytes plus 2 GiB.

The current 30,740/schema-2 observation is informative, not acceptance. The
post-freeze verifier establishes the actual migration count. The synthesis
plan must also be re-read because it changed during this review.

Verification:

```bash
set -euo pipefail
MIGRATION="$HOME/.local/state/rocket-agents/conversations/migration"
ARCHIVE="$HOME/.local/share/rocket-agents/conversations/archive.jsonl"
mkdir -p "$MIGRATION/preflight"
cd "$HOME/p/agents"
pnpm run conversations:verify-export -- \
  --archive "$ARCHIVE" --deep --json | \
  tee "$MIGRATION/preflight/local-archive.json" | \
  jq -e '.ok and (.manifest.records == .records) and ((.schemaCounts["1"] // 0) == 0)'
sync-conversations local inventory --json | tee "$MIGRATION/preflight/local-peer.json"
for route in peer-a peer-b; do
  sync-conversations "$route" inventory --json | tee "$MIGRATION/preflight/$route.json"
  jq -e '.reachable and .archivePresent and .archiveValid' "$MIGRATION/preflight/$route.json"
done
for route in peer-c-usb peer-c; do
  sync-conversations "$route" inventory --json | tee "$MIGRATION/preflight/$route.json"
done
jq -s -e '
  map(select(.reachable and .archivePresent and .archiveValid)) |
  (length >= 1) and (map(.installationFingerprint) | unique | length == 1)
' \
  "$MIGRATION/preflight/peer-c-usb.json" \
  "$MIGRATION/preflight/peer-c.json"
ARCHIVE_BYTES=$(stat -f '%z' "$ARCHIVE")
NEO_MIN_FREE=$((3 * ARCHIVE_BYTES + 2147483648))
jq --argjson minimum "$NEO_MIN_FREE" -e '.freeBytes >= $minimum' \
  "$MIGRATION/preflight/peer-a.json"
jq -s -e 'map(select(.reachable and .archivePresent) | .rocketAgentsCommit) | unique | length == 1' \
  "$MIGRATION/preflight/local-peer.json" \
  "$MIGRATION/preflight/peer-a.json" \
  "$MIGRATION/preflight/peer-b.json" \
  "$MIGRATION/preflight/peer-c-usb.json" \
  "$MIGRATION/preflight/peer-c.json"
cd "$HOME/p/atrium"
atrium rekey-synthesis | tee "$MIGRATION/preflight/synthesis-rekey-plan.txt"
atrium rekey-synthesis --repair --archive "$ARCHIVE" | \
  tee "$MIGRATION/preflight/synthesis-rekey-repair-plan.txt"
conversation-writers verify-running --all-peers
```

### Stage 5: freeze every writer, back up, and converge the legacy archives

This is the first stage that writes real canonical data. It may start only when
Stages 1-4 pass, all four installations run the same verified commits, every
archive validates, the `peer-a` capacity requirement passes, `peer-c` is online,
and the freeze-aware refresh script and SessionEnd hook are installed.

Freeze `com.cristian.sync-all-safe`, `com.cristian.atrium-refresh`, and the
SessionEnd path on each Mac; freeze the corresponding writer path on `peer-a`.
Wait for current writers rather than terminating them. Create byte-verified
archive backups on every holder. Then converge existing archives without any
provider capture. Run full four-peer cycles until two consecutive dry cycles
are zero. `peer-a` is included: its 10,134-record archive is real data, and its
failed full seed is unfinished work.

Verification:

```bash
set -euo pipefail
MIGRATION="$HOME/.local/state/rocket-agents/conversations/migration"
PEER_C_ROUTE=$(jq -r 'select(.reachable and .archivePresent) | .route' \
  "$MIGRATION/preflight/peer-c-usb.json" \
  "$MIGRATION/preflight/peer-c.json" | head -n 1)
test -n "$PEER_C_ROUTE"
conversation-writers freeze --all-peers
conversation-writers verify-frozen --all-peers
conversation-writers backup-archives --all-peers \
  --output "$MIGRATION/backups"
for pass in 1 2; do
  sync-conversations peer-a sync --migration-frozen --format v1
  sync-conversations "$PEER_C_ROUTE" sync --migration-frozen --format v1
  sync-conversations peer-b sync --migration-frozen --format v1
  sync-conversations peer-a dry --migration-frozen --format v1 --require-zero
  sync-conversations "$PEER_C_ROUTE" dry --migration-frozen --format v1 --require-zero
  sync-conversations peer-b dry --migration-frozen --format v1 --require-zero
done
cd "$HOME/p/agents"
pnpm run conversations:semantic-inventory -- \
  --archive "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" \
  --output "$MIGRATION/frozen-v1.semantic.jsonl"
pnpm run conversations:verify-peers -- \
  --reports "$HOME/.local/state/rocket-agents/conversations/migration" \
  --require-peers local,peer-a,peer-c,peer-b \
  --require-identical-manifest \
  --require-identical-semantic-digest \
  --require-verified-backups
```

### Stage 6: create and seed the first segment generation

Stream the frozen converged archive exactly once. Run every record through the
idempotent `upgradeConversationRecord`; report how many entered as schema 1 and
schema 2. Write one validated base segment without recapturing providers, so
archive-only conversations survive. Compare every ID, event body, metadata
field, and original provenance field; the deliberate schema/provenance mapping
is explicit, so raw record-hash equality is not a substitute for semantic
equality.

Re-key synthesis in the same frozen acceptance window. If the plan reports
legacy records, `--apply` must print the built-in backup path before moves and
must report zero collisions. If it reports zero legacy records, do not rewrite
it; verify the existing backup and idempotent zero plan. Rebuild a test Atrium
index from the materialized full export and compare raw records, both FTS lanes,
synthesis records, and vector identities with the pre-cutover inventory.

Seed the new generation to `peer-a`, `peer-c`, and `peer-b` while all writers
remain frozen. Do not remove `archive.jsonl`, its verified backups, or any old
generation.

Verification:

```bash
set -euo pipefail
MIGRATION="$HOME/.local/state/rocket-agents/conversations/migration"
ARCHIVE="$HOME/.local/share/rocket-agents/conversations/archive.jsonl"
SEGMENTS="$HOME/.local/share/rocket-agents/conversations/segments"
PEER_C_ROUTE=$(jq -r 'select(.reachable and .archivePresent) | .route' \
  "$MIGRATION/preflight/peer-c-usb.json" \
  "$MIGRATION/preflight/peer-c.json" | head -n 1)
cd "$HOME/p/agents"
pnpm run conversations:migrate-segments -- \
  --input "$ARCHIVE" --output "$SEGMENTS" --prepare-only \
  --report "$MIGRATION/segment-migration.json"
GENERATION_ID=$(jq -r '.generationId' "$MIGRATION/segment-migration.json")
pnpm run conversations:verify-segments -- \
  --archive "$SEGMENTS" --generation "$GENERATION_ID" --deep --json | \
  tee "$MIGRATION/segments-verify.json" | jq -e '.ok'
pnpm run conversations:semantic-inventory -- \
  --archive "$SEGMENTS" --generation "$GENERATION_ID" \
  --output "$MIGRATION/segments.semantic.jsonl"
pnpm run conversations:export-materialized -- \
  --archive "$SEGMENTS" --generation "$GENERATION_ID" \
  --output "$MIGRATION/materialized-full.jsonl"
pnpm run conversations:compare-semantic -- \
  --before "$MIGRATION/frozen-v1.semantic.jsonl" \
  --after "$MIGRATION/segments.semantic.jsonl" \
  --require-id-equality --require-event-byte-equality \
  --require-metadata-equality --require-fragment-provenance-preserved
cd "$HOME/p/atrium"
atrium rekey-synthesis | tee "$MIGRATION/synthesis-rekey-before.txt"
if grep -Eq 'would re-key [1-9][0-9]* records' "$MIGRATION/synthesis-rekey-before.txt"; then
  atrium rekey-synthesis --apply | tee "$MIGRATION/synthesis-rekey-apply.txt"
  grep -Fq 'records copied to ' "$MIGRATION/synthesis-rekey-apply.txt"
fi
atrium rekey-synthesis | tee "$MIGRATION/synthesis-rekey-after.txt"
grep -Fq 'would re-key 0 records' "$MIGRATION/synthesis-rekey-after.txt"
atrium rekey-synthesis --repair --archive "$ARCHIVE" | \
  tee "$MIGRATION/synthesis-rekey-repair.txt"
grep -Fq 'would repair 0 mis-stamped records' "$MIGRATION/synthesis-rekey-repair.txt"
uv run atrium --index "$MIGRATION/atrium-test.sqlite3" \
  ingest "$MIGRATION/materialized-full.jsonl"
uv run atrium --index "$MIGRATION/atrium-test.sqlite3" ingest-synthesis
uv run atrium --index "$MIGRATION/atrium-test.sqlite3" doctor \
  --archive "$MIGRATION/materialized-full.jsonl"
for route in peer-a "$PEER_C_ROUTE" peer-b; do
  sync-conversations "$route" seed-generation \
    --generation "$GENERATION_ID" --migration-frozen
  sync-conversations "$route" dry \
    --generation "$GENERATION_ID" --migration-frozen --require-zero
done
pnpm run conversations:activate-generation -- \
  --archive "$SEGMENTS" --generation "$GENERATION_ID"
for route in peer-a "$PEER_C_ROUTE" peer-b; do
  sync-conversations "$route" activate-generation \
    --generation "$GENERATION_ID" --migration-frozen
done
cd "$HOME/p/agents"
pnpm run conversations:verify-peers -- \
  --require-peers local,peer-a,peer-c,peer-b \
  --require-identical-generation \
  --require-identical-segment-set \
  --require-identical-materialized-state
```

### Stage 7: recovery drill, canary unfreeze, and measured acceptance

Before normal writers resume, copy the new generation into a disposable drill
root. Prove rebuild from segments with deleted disposable state. Run one sealed
generation erasure against a synthetic target injected only into the drill,
prove old-generation refusal and explicit reseed, then discard the drill root.

Unfreeze one trigger at a time. Run one local incremental capture and Atrium
partial ingest, synchronize all four installations, and immediately dry-run
them. Run the capture/publication benchmark five times and report p50 and max;
do not replace the baseline with a single favorable run.

Verification:

```bash
set -euo pipefail
MIGRATION="$HOME/.local/state/rocket-agents/conversations/migration"
PEER_C_ROUTE=$(jq -r 'select(.reachable and .archivePresent) | .route' \
  "$MIGRATION/preflight/peer-c-usb.json" \
  "$MIGRATION/preflight/peer-c.json" | head -n 1)
cd "$HOME/p/agents"
pnpm run conversations:recovery-drill -- \
  --archive "$HOME/.local/share/rocket-agents/conversations/segments" \
  --work "$MIGRATION/recovery-drill" \
  --exercise-erasure --exercise-stale-peer
conversation-writers unfreeze --trigger atrium-refresh --all-peers
conversation-writers verify-running --trigger atrium-refresh --all-peers
pnpm run conversations:capture -- --json | tee "$MIGRATION/canary-capture.json"
cd "$HOME/p/atrium"
atrium ingest --partial "$MIGRATION/pending-materialized.jsonl"
for route in peer-a "$PEER_C_ROUTE" peer-b; do
  sync-conversations "$route" sync
  sync-conversations "$route" dry --require-zero
done
cd "$HOME/p/agents"
pnpm run conversations:benchmark-segments -- \
  --trials 5 --artifacts 25000 --changed 1 \
  --max-capture-seconds 22.691 --max-import-seconds 6.618 \
  --require-warm-noop --require-proportional-bytes
conversation-writers unfreeze --all-peers
conversation-writers verify-running --all-peers
```

### Stage 8: retain rollback data; purge only by separate approval

Keep the legacy archive, its frozen checksum report, and the pre-cutover
synthesis backup through at least one successful recovery drill and an agreed
retention window. The migration does not delete them. Closing that window is a
separate destructive decision with an exact target inventory. A real
credential erasure invokes `conversations:erase`, requires all four managed
holders to acknowledge the new generation, and requires explicit approval to
purge old generations and affected backups.

Verification:

```bash
cd "$HOME/p/agents" && \
pnpm run conversations:retention-status -- \
  --archive "$HOME/.local/share/rocket-agents/conversations/segments" \
  --legacy "$HOME/.local/share/rocket-agents/conversations/archive.jsonl" \
  --require-recovery-drill \
  --require-no-automatic-purge
```

## Decision boundary for revisiting C

Revisit option C only when one of these becomes an accepted requirement:

- erasure must be available without freezing every writer;
- erasure frequency makes full-generation replacement operationally
  unacceptable;
- canonical history must be bounded by automatic online compaction;
- an offline peer must be able to create deletion intent that later converges
  without an operator-led reseed; or
- legal policy requires a durable, auditable deletion operation before the
  bytes can be compacted away.

Until then, sealed-generation replacement owns the consequence deliberately:
ordinary work stays small and auditable, while destructive work is rare,
global, previewed, and expensive enough that nobody can mistake it for source
absence or routine synchronization.

## Document verification

Run from this directory:

````bash
test -s DECISION.md && \
grep -Fq 'Choose **F with a named erasure mechanism: sealed-generation replacement**' DECISION.md && \
grep -Fq 'What breaks if this call is wrong' DECISION.md && \
grep -Fq 'Stage 1 creates exactly these files' DECISION.md && \
grep -Fq 'This is the first stage that touches real data, and it is read-only' DECISION.md && \
grep -Fq 'This is the first stage that writes real canonical data' DECISION.md && \
grep -Fq '16,148 legacy plus 489 current records' DECISION.md && \
grep -Fq 'local,peer-a,peer-c,peer-b' DECISION.md && \
grep -Fq '132.36 seconds' DECISION.md && \
grep -Fq '226.91 seconds' DECISION.md && \
grep -Fq '30,740 valid records' DECISION.md && \
test "$(grep -c '^### Stage [1-8]:' DECISION.md)" -eq 8 && \
test "$(( $(grep -c '^```' DECISION.md) % 2 ))" -eq 0 && \
! grep -Eq 'TODO|TBD|PLACEHOLDER' DECISION.md
````

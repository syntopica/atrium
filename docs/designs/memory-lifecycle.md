# Memory lifecycle: distil, forget, then delete

Status: proposed 2026-10-14. Owner direction, same day: "if this is a memory
and a brain I do not want to keep junk for years"; keep what is worth keeping,
and remove what is retired, superseded or no longer relevant - "as if we had
never used MemPalace and only had Atrium". The image the owner gave: a storage
room of clean shelves holding what matters, with the rubbish out, instead of
one full of dirty, unsorted boxes.

## What is wrong today

Atrium keeps everything and ranks it. Since 2026-10-14 the admission rule keeps
tool calls and their results out (1.92M records down to 484k), and declared
retirements rank outdated mentions last. Ranking still serves the junk, though,
just lower down, and nothing ever leaves:

- 412,475 user/assistant records over 30,158 conversations, plus 65,236
  synthesis records. Every conversation stays raw, in full, for good.
- Retired subjects stay in history. Records naming each term before its
  retirement date, as of 2026-10-14: MemPalace 5,764 (spread over 4,270
  conversations, because its hooks injected text into nearly every session),
  Holded 7,230, cPanel/WHM 4,451, `~/p/vault` 514, Gemini CLI 64.
- Projects the owner no longer works on compete with live ones in every search.
- When a decision changes partway through a project (one library swapped for
  another), both versions are served side by side, and nothing marks the older
  one as superseded.

The pieces for the fix already exist: per-session episodes, the claim
extraction pilot (497 claims in `curation/claims.jsonl`), near-duplicate pairs,
equivalence clusters, and the `pair_relation` judge. What is missing is a
lifecycle to connect them, and permission to let things go.

## The target shape

Agents read three kinds of material, and raw transcript is not one of them for
long:

1. **Brain pages**, curated by hand: unchanged.
2. **Facts**: short, sourced claims distilled from conversations, deduplicated,
   each carrying its project, first/last seen dates, and the episodes it came
   from. This is the durable layer.
3. **Episodes**: one summary per session. They stay for as long as their
   project is live.

Raw records are a recent buffer: they stay searchable until their conversation
is distilled and the distillation has been checked, and then they leave the
index.

## Lifecycle

Every record, episode and fact is in exactly one state:

```
active --forget--> forgotten --(curation window passes)--> deleted
   ^                   |
   +---- restore ------+
```

- **active**: indexed and served.
- **forgotten**: out of the index and out of every answer, but listed in the
  forget ledger. It can be restored with one command. The archive still holds
  it.
- **deleted**: once the curation window has passed (default 30 days) with no
  restore, the item is removed from the synthesis registry and the curation
  files (see Final deletion). There is no restore after this point.

### The ledger

`<instance>/forget/ledger.jsonl` (`forget.path` in the instance config) is an
append-only event log, tracked in the instance repository: the index is
disposable, the ledger is policy, and both machines must forget the same
things. It holds identifiers, never text. One line per event:

```json
{"event": "forget", "record_id": "...", "rule": "retired", "rule_version": 1,
 "detail": "Holded", "at": "2026-10-14"}
{"event": "restore", "record_id": "...", "at": "2026-10-20"}
```

A record is forgotten while its latest event is `forget`. A `restore` pins
it: a later run of any rule skips a record whose latest event is `restore`,
so restoring is not undone by the next pass. Keys are record ids, so a raw
record (conversation plus event id) keeps its key across re-ingests; an
episode whose synthesis is regenerated gets a new id and is judged again.

Forgetting is applied by admission, not by mutating the index: `ingest` and
`ingest-synthesis` turn away ledgered ids under the rule `forgotten`, the row
hash of the conversation changes, and the supported rewrite path replaces its
rows; the context service rebuilds its dense matrix from the new index
generation. Until the next refresh the rows are still served, which
`atrium forget --apply` states.

A forget reason is always one of a closed set, so a later audit can count by
rule. Every rule writes a report first and applies only with `--apply`.

### Forget rules

1. **Retired** (`retired`): a record or episode authored **before** the
   retirement date that names one of its terms. Those are the records that
   describe the retired thing as current. Later records stay: they are
   mostly "X is retired, use Y" and the migration itself, which is what keeps
   an agent from proposing X again. Retirements move out of the pages they
   lived on and into one list, `brain/retired.md` (one `retired:` block per
   section), so the page about the retired tool can be deleted once its
   still-true facts are moved to live pages by hand. Curated notes are never
   forgotten by rule: the brain is edited by its owner.
2. **Distilled** (`distilled`): a conversation's raw records leave the index
   once its distillation is complete and checked. The 85-question acceptance
   set is not enough for that check, since it says nothing about the
   conversations it does not sample, and a retrieved hit does not prove that a
   qualification survived. The gate is per conversation and bound to its
   source revision: every claim-bearing record maps to a fact or an episode
   sentence that keeps its qualifications, extraction failures fail closed, and
   a held-out answer evaluation runs against a baseline frozen before any
   forgetting.
3. **Superseded** (`superseded`): the pair judge gains a `supersedes`
   relation, but date order is not evidence. The judge has to find the same
   entity, scope and conditions, and a stated replacement ("moved from X to
   Y"), and it keeps the all-pairs equivalence and numeric veto it has today.
   The older fact is forgotten, and so is episode text that carries only that
   fact.
4. **Duplicate** (`duplicate`): one fact per equivalence cluster survives (the
   newest, with every source merged in). The others are forgotten.
5. **Inactive project** (`inactive-project`): a project with no session for a
   window the owner sets, *listed for the owner's confirmation* (a project is
   never inferred dead), loses its episodes and raw records. Its facts stay, so
   a later "how did we deploy X" still answers.
6. **Wrong** (`wrong`): a fact the owner or a later session marks as false.

### Restore

`atrium forget --restore <record id|rule>` appends restore events, and the
next ingest admits the records again. A context answer whose question names a
retired term says how many records the `retired` rule forgot for it and gives
the restore command. It does not serve the forgotten text.

## Final deletion

Deletion is the only irreversible step, and it runs only on items whose window
has expired:

- synthesis registry files and curation rows: deleted by Atrium under the
  erase lock, the way `atrium erase` does for whole conversations;
- the archive is not Atrium's to delete. Admission skips tool results and
  other events that never reach the index, so an archive deletion has to
  cover the complete source and is a separately authorized scribe operation,
  per conversation today and per event once scribe's v2 tombstones and
  `conversations:redact` land (design 2.8). `atrium erase` then follows the
  applied archive plan, as it does now.

## Order of work

1. **Retired forgetting.** `brain/retired.md`; the ledger; admission in
   ingest and ingest-synthesis; `atrium forget --rule retired [--apply]` with
   a report first; restore; the context line. Archive deletion and brain edits
   stay out of the code.
2. **Distillation at scale.** Extend the claim pipeline from the 497-claim pilot
   to every conversation, routed agy -> OpenRouter -> local (Codex only to
   verify). Measure cost and coverage on 200 conversations first.
3. **Supersession and duplicates** over the full fact set.
4. **Distilled forgetting**, behind the per-conversation gate.
5. **Inactive projects**, with an owner-confirmed list.
6. **Final deletion** of expired items in Atrium's own stores, then the scribe
   archive operation.

## Acceptance

- Phase 1: after a refresh, no admitted record authored before a retirement
  names one of its terms; a context question naming the term gets the
  "forgotten, restorable" line; a restore survives the next `forget --apply`
  and the record is back after the next ingest; tests cover restart, rebuild
  from an empty index, and a crash between ledger write and ingest.
- Every phase: `evaluations/acceptance-2026-10-11` (85 questions, lanes.json
  recaptured on the clean index) does not lose a hit it had before. Index size,
  and the record counts per reason, are reported in `atrium status`.

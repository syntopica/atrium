# Which model should synthesize, and at what effort

Measured 2026-09-01, on this machine, against the live archive.

## Why it was measured

Synthesis quality *is* semantic search quality here: dense vectors cover only
synthesized content. The lane that was doing whole-corpus work (Gemini via
`agy`) has been asleep against its weekly quota wall since 2026-08-31, and
coverage was falling rather than rising — 3,007 of 30,318 archived
conversations, 9.9%, against 23.7% when the denominator was smaller. The Codex
lane has headroom (Pro 20x, weekly window at 11%), but its account default is
`gpt-5.6-sol` at **high** reasoning effort, which is the wrong price for a task
the design itself calls extraction rather than judgement.

So: what is the cheapest configuration that is still trustworthy?

## Method

Three real episodes, none previously synthesized, drawn from the live archive
and spanning 4k-40k characters of transcript, in the corpus's own languages.
Each ran through four configurations with the production prompt, the production
tool schema and `--output-schema` enforcement — the same path
`codex_lane_call` takes.

A fourth model then ranked the four outputs per episode **blind**: labels
shuffled, no model names, the verbatim transcript supplied first, graded on
faithfulness to the transcript, exact recall of names/versions/paths/numbers,
actionable durability, language match, and honest open ends. Any claim not
supported by the transcript had to be listed explicitly.

## Result

| configuration | wall time / episode | fabrications | blind rank |
| --- | --- | --- | --- |
| `gpt-5.6-sol` high (account default) | 34.6 s | 0 | 1st, 1st, 1st |
| `gpt-5.6-terra` medium | 16.5 s | 0 | 4th, 2nd, 2nd |
| `gpt-5.6-terra` low | **15.4 s** | **0** | 3rd, 3rd, 3rd |
| `gpt-5.6-sol` low | 28.4 s | **3** | 2nd, 4th, 4th |

**The obvious way to save money is the one that breaks.** Dropping the big
model's reasoning effort from high to low did not merely lose polish — it
started inventing. Three unsupported claims across two of the three episodes:
a normalization pipeline attributed to both sides of a comparison when the
transcript showed it on one, a manifest reported as 40 pairs when the
transcript said 36, and a narrow rule about meal receipts restated as a
universal one. In a memory system a fabricated fact is worse than a missing
one, because it is indistinguishable from a real one months later.

Switching to the **smaller** model instead cost nothing in faithfulness: zero
fabrications at either effort, while running 2.2x faster than the default
configuration. The quality gap to `sol` high is real but it is a gap in
richness and framing, not in truthfulness.

## Decision

Bulk synthesis runs on **`gpt-5.6-terra` at low effort**. It is the cheapest
configuration with no measured fabrication, and cost is the binding constraint:
roughly 150,000 episodes remain (5.5 episodes per conversation, measured over
300 conversations), so a 2.2x difference in per-episode cost decides whether
the corpus is reachable at all.

`terra` medium ranked above `terra` low in two of three episodes for 7% more
time, which on n=3 is too weak a signal to pay for at this scale. Revisit if a
larger sample separates them.

The population is named `gpt-5.6-terra-low` and appended **last** in
`active-recipe.json`, so it never outranks output already paid for — it serves
only episodes no other population covers.

## Confirmed in production the same day

A bounded pass over the newest 150 conversations, `--producer codex --model
gpt-5.6-terra --effort low --workers 4`: **114 episodes synthesized, 760
already present, 0 failed conversations.** Compare the agy lane's last logged
pass on the same corpus: `failed=30620`. Spot-checked records reproduce file
paths, flag names and field lists exactly, and record `model_resolved:
gpt-5.6-terra` with `event_id_schema: 2`.

Reliability is the second argument for this lane, independent of price: the
walled lane does not merely go slowly, it spends its wall-clock producing
nothing.

## The cheapest model does not make the corpus affordable

Worth stating plainly, because the bench invites the opposite conclusion. The
Codex weekly window read 11% before the production pass and 11% after it, with
114 synthesis calls in between — so one percentage point is worth more than 114
calls, and the whole weekly window is on the order of twelve thousand. Against
~150,000 remaining episodes that is roughly a dozen weekly cycles on this lane,
the same order of magnitude as the Gemini lane it replaces.

What the cheaper model buys is real but bounded: 2.2x less wall-clock per
episode, and a lane that actually produces (0 failed conversations against
`failed=30620`). What it does not buy is a corpus-complete backfill. The
remaining lever is not price per call, it is deciding that full coverage is not
the goal — synthesize newest-first, continuously, and accept a coverage
frontier that moves forward rather than a corpus that is ever finished.

## What this does not settle

Whether the answers actually get *better* — that still needs the hand-labeled
acceptance set the Measurement item in `TODO.md` is blocked on. This bench
measures faithfulness against a transcript, which is the property a synthesis
must not violate; it does not measure retrieval quality.

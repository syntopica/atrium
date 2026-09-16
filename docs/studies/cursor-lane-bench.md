# Which Cursor model should synthesize

Measured 2026-09-16, on this machine, against the live archive, on the day the
lane was added.

## Why it was measured

Operator directive, 2026-09-16: bulk synthesis must not spend the Codex
account's quota, which is the same quota interactive Codex work spends. The
lanes left are agy (Gemini through the Antigravity CLI) and Cursor. agy has
been walled or blind since 2026-08-31: its last pass on 2026-09-05 ended with
"Individual quota reached ... Resets in 127h", and since then CodexBar reports
no Antigravity limits at all (`Limits: not available`), so `drip-quota.py`
answers its blind 1800 s for that provider and never sees headroom. Cursor's
monthly window sat at 9.8% used with a reset on 2026-10-10 and had never been
used for synthesis.

The Cursor CLI exposes a model list rather than one account default, so the
question was which of its cheap models is faithful, using the method of the
[producer bench](synthesis-producer-bench.md): the same production prompt and
tool schema, real unsynthesized episodes, fabrications counted against the
transcript.

## Method

Three real episodes, none previously synthesized, the newest single-chunk
episode from each of three projects (8k, 10k and 20k characters of transcript,
Spanish and English). Each ran through three models via the production path
`cursor_lane_call` (`cursor-agent -p --mode ask --output-format json`, prompt
on stdin):

- `gpt-5.3-codex-low`
- `gemini-3.7-flash-high` (the same family the agy population is built on)
- `cursor-grok-4.6-low`

The outputs were judged in-session against the verbatim transcripts by the
operator's Claude session, not by a fourth model: every claim was checked for
support in the transcript, and the unsupported ones listed.

## Result

| model | wall time / episode | fabrications | character |
| --- | --- | --- | --- |
| `gpt-5.3-codex-low` | **15-23 s** | **0** | exact commit ids, exit codes, paths, test counts; open ends name what was not done |
| `gemini-3.7-flash-high` | 21-27 s | 0 | faithful, fewer facts, one "expected" clone list restated as established |
| `cursor-grok-4.6-low` | 41-46 s | 2 | "clean detached HEAD" with no `git status` output in the transcript; a sweep window asserted for a day the log excerpt did not show |

Both unsupported grok claims are small, and both are the kind that reads as a
real fact months later. The two faithful models differ in richness rather than
truthfulness, and the richer one is also the faster one.

Every call carries about 24,000 input tokens of the CLI's own context before
the episode (measured on a 90-character probe), so the reported `usage` is
dominated by overhead on short episodes.

## Cost

CodexBar's Cursor reading updates lazily, so per-call deltas came back as
zero; measured in aggregate instead: 13 calls moved the "Total" window from
9.822% to 9.887%, about **0.005% per episode**, or roughly **18,000 episodes
per monthly window**. With 90% of the window left that is on the order of
16,000 episodes before the 2026-10-10 reset, the same order as one Codex
weekly window without touching the Codex account. The "Third Party" window
CodexBar shows at 100% is the `tertiary` one `drip-quota.py` does not read,
and calls succeed with it spent, so it does not gate this lane.

## Decision

The Cursor lane runs **`gpt-5.3-codex-low`**: zero measured fabrications, the
fastest of the three, and the richest recall. The population is named
`cursor-gpt-5.3-codex-low` and appended **last** in `active-recipe.json`, so
it serves only episodes no paid-for population already covers.

Workers start at 3, the agy lane's measured optimum; Cursor's server-side rate
limiting has not been measured and nothing here argues for more.

## What this does not settle

n=3, as before. Whether Cursor rate-limits parallel workers the way agy does,
and whether the monthly window is spent evenly by model, are both to be read
off the drip's `run.log` and CodexBar after the first day.

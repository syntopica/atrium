# Acceptance set

"Better than memstore" becomes a number only against questions whose correct
answers a human has confirmed. The 365/389-pair sets used during design were
machine-extracted; they shaped the architecture but are not valid for
production decisions -- the extractor favors questions that share words with
their answers, which is exactly the variable under test.

## What a labeled pair is

One line of `labeled.jsonl`:

```json
{"question": "por que se revirtio WAL",
 "answer_conversation_id": "<id of the conversation that answers it>",
 "strata": ["es", "conversation", "overlap"],
 "notes": "optional"}
```

The answer is a conversation id (from `atrium search` output), not a record id:
judging at record granularity punishes retrieval for returning a different but
equally correct passage of the same conversation.

## Strata

Label each question with one tag from each group, and keep the set roughly
balanced across them:

- Language: `es` | `en`
- Where the answer lives: `conversation` | `note`
- Lexical relation: `overlap` (question shares informative words with the
  answer) | `no-overlap` (it shares none -- the class where lexical retrieval
  scores 0% and only the dense lane can work). Aim for at least 12
  `no-overlap` questions; they are the hardest to write and the whole reason
  the dense lane exists.
- Age: `recent` (this month) | `old` (anything earlier), so recency bias in
  ranking shows up.

## How to label

1. Write a question you actually remember the answer to.
2. Find the conversation that answers it: `atrium search "..." --limit 10`
   (try `--words`, `--dense` and `--substring`; the point is finding the true
   answer, not testing a lane).
3. If no lane finds it, locate it in the archive by other means (grep the
   export) -- a question retrieval cannot find yet is the most valuable kind.
   Do not drop it.
4. Append the line to `labeled.jsonl`.

Target: 60+ questions. `candidates.jsonl` holds unlabeled drafts to react to
-- rewrite them in your own words rather than accepting them as-is, because
questions phrased by the same model that wrote the corpus summaries
overestimate retrieval.

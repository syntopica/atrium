"""The lexical share of fusion in the curated-notes pass."""

# Measured 2026-10-11 on the 85-question acceptance set (GPT-6 labelled, audited;
# instance state `atrium/evaluations/acceptance-2026-10-11/`): on its 20 note
# questions the curated pass scored R@10 / MRR@10 0.50 / 0.40 at the history
# weight of 0.7, 0.60 / 0.47 at 0.5 and 0.70 / 0.50 at 0.3 (dense alone 0.65 /
# 0.46). Notes are curated prose a question paraphrases rather than quotes, so
# the dense lane carries them. History moved to 0.5 once the reranker was on
# (see `history_lexical_weight.py`); curated re-measured then: 0.15 changed nothing
# and 0.5 lost 3 questions.
CURATED_LEXICAL_WEIGHT = 0.3

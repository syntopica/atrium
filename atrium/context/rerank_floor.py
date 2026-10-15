"""The cross-encoder logit below which a reranked candidate is not evidence."""

# gte-multilingual-reranker at 256 tokens, measured 2026-10-15 on both
# evaluation sets (ranking-2026-10-15): dropping candidates under -0.8 lost no
# answer on either and removed about half an item per holdout answer; -0.5
# lost one. Its logits are compressed: answered questions' best evidence sits
# around 0.8, unanswered ones' around -0.2. Re-measure with any other model.
RERANK_FLOOR = -0.8

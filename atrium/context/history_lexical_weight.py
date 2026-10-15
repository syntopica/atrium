"""The lexical share of fusion in the history pass of a context answer."""

# Measured 2026-10-15 with the reranker on (gte at 256 tokens), end to end through
# `retrieve_context`, R/MRR at 8 (instance `atrium/evaluations/retrieval-2026-10-15/`):
# acceptance (85) 0.39/0.22 at 0.7 and 0.40/0.25 at 0.5 (gained 3, lost 2); held-out
# (88) 0.50/0.39 and 0.52/0.43 (gained 2, lost 0); 0.85 changed nothing. The
# reranker reorders what fusion admits, so a wider dense share in the 32 fused
# candidates pays off here. `atrium search` has no reranker and keeps
# `fuse_ranked`'s 0.7, measured for it.
HISTORY_LEXICAL_WEIGHT = 0.5

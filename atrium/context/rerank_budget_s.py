"""How long reranking may add to one context answer, in seconds."""

# Owner's choice, 2026-10-15: about 2 s more per answer is worth +0.08-0.11
# recall at 8; past 3 s the fused order is served instead.
RERANK_BUDGET_S = 3.0

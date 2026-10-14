"""How long reranking may add to one context answer, in seconds."""

# The plan's ceiling for shipping the reranker at all: added p95 under 1.5 s.
RERANK_BUDGET_S = 1.5

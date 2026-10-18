"""Time an answer still needs after reranking, in seconds."""

# Links, evidence selection and the JSON reply took well under 0.2 s in the
# 2026-10-18 profile (4.2 s request, 3.08 s of it rerank); 0.5 s leaves room
# for a loaded machine without giving the rerank budget away.
FINISH_MARGIN_S = 0.5

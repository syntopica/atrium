"""Which record roles earn a vector."""

# Vectors cover meaning, not bulk: curated notes and session synthesis. Raw
# conversation stays lexical-only -- a deterministic filter removes just 27.5%
# of it (measured), leaving 972,760 vectors at 1.49 GB per brute-force query,
# which is the scale that forced the previous system onto an ANN index and paid
# for it in compaction failures, SIGBUS crashes and a watchdog.
SEMANTIC_ROLES = ("note", "synthesis")

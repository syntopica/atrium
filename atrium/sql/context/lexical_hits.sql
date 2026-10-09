-- The scope reaches the FTS table as a join. Constraining it with
-- `rowid IN (...)` instead makes FTS5 re-run the match per candidate rowid:
-- 13.57s against 0.04s for the same curated query, same rows. The rank
-- ordering is what `ranked_hits` streams; a LIMIT here would defeat it.
WITH eligible AS MATERIALIZED (
    SELECT r.rowid FROM records r WHERE 1 = 1{scope}
)
SELECT r.record_id, r.text, -bm25({table}), r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM {table}
JOIN eligible e ON e.rowid = {table}.rowid
JOIN records r ON r.rowid = {table}.rowid
WHERE {table} MATCH ?
ORDER BY {table}.rank

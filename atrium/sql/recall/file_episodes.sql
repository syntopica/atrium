-- This project's synthesized episodes that name one file, newest first. The
-- match runs once over the word index and the scope filters its rows: a file
-- name is rare enough that the matched set is small, where scoping first
-- would scan every record of a large project.
WITH matched AS MATERIALIZED (
    SELECT rowid FROM words WHERE words MATCH ?
)
SELECT r.record_id, r.text, r.conversation_id, r.source_sha256, r.authored_at,
       r.provider, r.role
FROM matched m
JOIN records r ON r.rowid = m.rowid
WHERE r.role = 'synthesis'
  AND (r.workspace = ? OR substr(r.workspace, 1, length(?) + 1) = ? || '/')
ORDER BY r.authored_at DESC, r.conversation_id, r.record_id
LIMIT ?

SELECT r.record_id, r.text, -bm25(substrings) AS score, r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM substrings
JOIN records r ON r.rowid = substrings.rowid
WHERE substrings MATCH ?{scope}
ORDER BY bm25(substrings)
LIMIT ?

SELECT r.record_id, r.text, -bm25(words), r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM words JOIN records r ON r.rowid = words.rowid
WHERE words MATCH ?
ORDER BY words.rank

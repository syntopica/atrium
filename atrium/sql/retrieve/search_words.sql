-- FTS5 bm25() returns MORE NEGATIVE values for better matches. Negating it here
-- means every lane reports "higher is better", so fusion does not have to
-- special-case one lane's sign.
SELECT r.record_id, r.text, -bm25(words) AS score, r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM words
JOIN records r ON r.rowid = words.rowid
WHERE words MATCH ?{scope}
ORDER BY words.rank

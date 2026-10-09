SELECT v.record_id, v.vector, r.text, r.conversation_id, r.source_sha256,
       r.authored_at, r.provider, r.role
FROM vectors v
JOIN records r ON r.record_id = v.record_id
WHERE 1 = 1{scope}
ORDER BY v.record_id

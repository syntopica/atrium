SELECT record_id, text, conversation_id, source_sha256, authored_at, provider, role
FROM records
WHERE record_id IN ({placeholders})

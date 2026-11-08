-- Frozen retrieval-only corpus. Intentionally enumerate the semantic layer.
SELECT r.record_id, r.event_id, r.conversation_id, r.source_sha256, r.provider,
       r.role, r.text, r.authored_at, r.workspace, r.title, r.event_index, v.vector
FROM vectors v JOIN records r ON r.record_id = v.record_id
WHERE r.role IN ('note', 'synthesis')
ORDER BY r.record_id

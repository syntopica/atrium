SELECT conversation_id, text
FROM records
WHERE role = 'note' AND text LIKE '%retired:%'
ORDER BY conversation_id, event_index

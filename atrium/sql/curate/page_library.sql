SELECT r.conversation_id, r.title, r.text, v.vector
FROM records r
LEFT JOIN vectors v ON v.record_id = r.record_id
WHERE r.provider = 'brain'
ORDER BY r.record_id

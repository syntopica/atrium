SELECT conversation_id, min(workspace)
FROM records
WHERE workspace IS NOT NULL AND provider != 'synthesis'
GROUP BY conversation_id

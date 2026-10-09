SELECT conversation_id, workspace, COUNT(*)
FROM records
WHERE conversation_id IN ({placeholders}) AND workspace IS NOT NULL
GROUP BY conversation_id, workspace

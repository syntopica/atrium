DELETE FROM conversation_revisions WHERE provider = ?
AND conversation_id NOT IN (SELECT id FROM seen_conversations)

SELECT workspace,
       count(DISTINCT CASE WHEN provider != 'synthesis' THEN conversation_id END) AS conversations,
       count(CASE WHEN provider = 'synthesis' THEN 1 END) AS episodes
FROM records
WHERE workspace IS NOT NULL AND provider != 'brain'
GROUP BY workspace

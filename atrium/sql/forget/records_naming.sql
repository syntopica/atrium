SELECT record_id, role, text
FROM records
WHERE role IN ('user', 'assistant', 'synthesis')
  AND authored_at < :since
  AND text LIKE :pattern

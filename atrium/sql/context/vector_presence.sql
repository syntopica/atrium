SELECT 1
FROM vectors v
JOIN records r ON r.record_id = v.record_id
WHERE 1 = 1{scope}
LIMIT 1

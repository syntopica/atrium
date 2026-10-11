-- Driven from vectors, never from records: ordering by r.record_id let the
-- planner walk all of records by primary key and read every row to test its
-- role, which took 213 s unscoped on 1.86M records (2026-10-11). The vectors
-- are the ~70k rows that can match; CROSS JOIN pins that order.
SELECT r.record_id, r.text, r.conversation_id, r.source_sha256, r.authored_at, r.provider, r.role,
       v.vector
FROM vectors v
CROSS JOIN records r ON r.record_id = v.record_id
WHERE 1 = 1{scope}
ORDER BY v.record_id

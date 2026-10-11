-- No FROM on the outer SELECT: once the row exists the WHERE yields nothing and the
-- scalar count is never evaluated. `INSERT OR IGNORE ... SELECT count(*) FROM records`
-- would scan the whole table on every writable open only to discard the result.
INSERT INTO record_total (k, n)
SELECT 1, (SELECT count(*) FROM records)
WHERE NOT EXISTS (SELECT 1 FROM record_total)

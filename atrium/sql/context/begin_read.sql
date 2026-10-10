-- A read transaction: under WAL every statement until the matching COMMIT
-- sees one snapshot of the index.
BEGIN

-- `INSERT OR REPLACE` into vectors fires this too, so a re-embedded record
-- counts as a change even when the row count stays the same.
CREATE TRIGGER IF NOT EXISTS vectors_generation_ai AFTER INSERT ON vectors BEGIN
    UPDATE dense_generation SET n = n + 1 WHERE k = 1;
END

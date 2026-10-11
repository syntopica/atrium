CREATE TRIGGER IF NOT EXISTS records_total_ad AFTER DELETE ON records BEGIN
    UPDATE record_total SET n = n - 1 WHERE k = 1;
END

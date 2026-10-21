INSERT INTO record_hosts (record_id, hosts_json) VALUES (?, ?)
ON CONFLICT (record_id) DO UPDATE SET hosts_json = excluded.hosts_json
WHERE record_hosts.hosts_json != excluded.hosts_json

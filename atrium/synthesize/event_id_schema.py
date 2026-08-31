"""Which event id rule a synthesis record's member ids follow."""

# 2 since 2026-08-31, when Rocket Agents bound an event id to its conversation.
# A record written before that carries no `event_id_schema` field at all, and
# absence is what the re-key reads as 1: back-filling the field would have
# required rewriting every record to say what its absence already says.
EVENT_ID_SCHEMA = 2

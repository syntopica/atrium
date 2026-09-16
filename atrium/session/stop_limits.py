"""Reminder limits of the Stop decision: when a session owes a record."""

# These bound how much unrecorded transcript a session may carry; they are
# not episode semantics. Under them the conversation is left to the batch
# lanes, which is what those lanes are for.
MIN_NEW_BYTES = 32 * 1024
MIN_NEW_BYTES_AGED = 4 * 1024
MAX_UNRECORDED_SECONDS = 1800
# Refusals per checkpoint before the hook goes quiet and leaves it pending
# for the next ordinary turn (Claude Code itself gives up after eight).
MAX_ATTEMPTS = 3

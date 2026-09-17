"""Reminder limits of the Stop decision: when a session owes a record."""

# These bound how much unrecorded work a session may carry; they are not
# episode semantics. Under them the conversation is left to the batch lanes,
# which is what those lanes are for.
#
# Prompts, not bytes. Measured on one real engineering session on 2026-09-17:
# the seven intervals between its records held 89 KB to 690 KB of eligible
# transcript and 1 or 2 prompts each. A byte limit of 32 KiB is crossed by a
# single turn -- tool results are `user` records and long answers are large --
# so the hook refused the stop after every turn and the person read a red
# "Stop says" line each time. What tracks work worth an episode is how many
# times the person asked for something.
MIN_NEW_PROMPTS = 3
# The age rule is the loss bound: any real work is recorded within the window
# even when the conversation is one long prompt. Replayed over that same
# session's 56 prompts, the old rule refused 48 stops -- one per prompt. With
# three prompts and this window it refuses 20; at 30 minutes it refuses 27,
# and the extra half hour of tail is a conversation the batch lanes synthesize
# anyway.
MIN_NEW_BYTES_AGED = 4 * 1024
MAX_UNRECORDED_SECONDS = 3600
# Refusals per checkpoint before the hook goes quiet and leaves it pending
# for the next ordinary turn (Claude Code itself gives up after eight).
MAX_ATTEMPTS = 3

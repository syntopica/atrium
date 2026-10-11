"""The temporary directory the synthesis lane ran codex in."""

# `codex_lane_call` ran each synthesis job in a `TemporaryDirectory(prefix=
# "atrium-codex-")`: 43,085 archived conversations by 2026-10-11 whose user turns
# are Atrium's own synthesis prompts, and whose synthesis re-summarised episodes
# already summarised. Exact on purpose: a person can work from a temporary
# directory too, so `/T/` alone is no evidence of automation. Each further
# automation prefix needs its creator found first (see TODO.md).
ATRIUM_CODEX_WORKSPACE = r"^(?:/private)?/var/folders/[^/]+/[^/]+/T/atrium-codex-[^/]+/?$"

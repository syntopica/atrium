"""Warnings that are bookkeeping, not a sign that retrieval fell short."""

# Kept in step with ROUTINE in plugins/atrium-context/hooks/degradation.js.
# `no_matches` is an answer; a full candidate pool is already `truncated`; a
# deduplicated parent, an unresolved or unsafe link and an invalid note path
# are a note's own state and are skipped by design; a stale dense matrix still
# serves while a newer one builds. Each one is still listed in `warnings`.
ROUTINE_WARNINGS = frozenset(
    {
        "no_matches",
        "retrieval_candidate_limit_reached",
        "linked_parent_deduplicated",
        "unresolved_indexed_link",
        "unsafe_link_ignored",
        "invalid_note_path",
        "dense_matrix_stale_rebuilding",
    }
)

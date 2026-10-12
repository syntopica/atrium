// The warnings that say retrieval did not fully happen, as one short phrase.
// `no_matches` is an answer, three are routine bookkeeping, a note whose path
// or links point outside the wiki has them skipped by design, and a dense
// matrix still serving while a newer one builds answers from slightly older
// vectors: none of them is worth a warning on every prompt.
const ROUTINE = [
  'no_matches',
  'retrieval_candidate_limit_reached',
  'linked_parent_deduplicated',
  'unresolved_indexed_link',
  'unsafe_link_ignored',
  'invalid_note_path',
  'dense_matrix_stale_rebuilding',
]

export function degradation(answer) {
  const warnings = (answer?.warnings ?? []).filter((warning) => !ROUTINE.includes(warning))
  return warnings.join(', ')
}

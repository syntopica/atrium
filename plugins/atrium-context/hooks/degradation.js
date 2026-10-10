// The warnings that say retrieval did not fully happen, as one short phrase.
// `no_matches` is an answer, two are routine bookkeeping, and a dense matrix
// still serving while a newer one builds answers from slightly older vectors:
// none of them is worth a warning on every prompt.
const ROUTINE = ['no_matches', 'retrieval_candidate_limit_reached', 'unresolved_indexed_link', 'dense_matrix_stale_rebuilding']

export function degradation(answer) {
  const warnings = (answer?.warnings ?? []).filter((warning) => !ROUTINE.includes(warning))
  return warnings.join(', ')
}

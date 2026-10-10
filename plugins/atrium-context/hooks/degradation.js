// The warnings that say retrieval did not fully happen, as one short phrase.
// `no_matches` is an answer, and the two dropped here are routine bookkeeping.
const ROUTINE = ['no_matches', 'retrieval_candidate_limit_reached', 'unresolved_indexed_link']

export function degradation(answer) {
  const warnings = (answer?.warnings ?? []).filter((warning) => !ROUTINE.includes(warning))
  return warnings.join(', ')
}

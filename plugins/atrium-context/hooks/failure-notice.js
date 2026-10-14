// Said instead of nothing when retrieval fails: silence reads as "nothing on
// record", and a session once told the owner a mail was unanswered that had
// been answered because both retrievals had timed out (2026-10-09).
export const FAILURE_NOTICE = [
  '# atrium context unavailable for this prompt',
  '',
  'Retrieval failed or timed out twice, so nothing was checked: this is not',
  'an empty record, and the machine may be saturated. Before stating',
  'anything about prior work, people, threads or decisions, call',
  '`atrium_context` (or `atrium context`) yourself, retrying once if it',
  'times out, and check the live source.',
].join('\n')

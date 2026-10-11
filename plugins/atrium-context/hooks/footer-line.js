import { usageNotice } from './usage-notice.js'

// The green line: what was retrieved for the prompt, then how the turn used
// the brain; '' when there is neither.
export function footerLine(summary, usage) {
  const notice = usageNotice(usage)
  if (!summary) return notice ? 'Atrium · ' + notice : ''
  return notice ? summary + ' · ' + notice : summary
}

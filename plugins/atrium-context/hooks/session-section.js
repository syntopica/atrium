import { approxTokens } from './approx-tokens.js'
import { counted } from './counted.js'
import { formatDuration } from './format-duration.js'

// The session's totals: searches, failures, retries, the usual wait, and what
// was handed to Claude.
export function sessionSection(stats) {
  const failed = stats.failures ? counted(stats.failures, 'failed', 'failed') : 'none failed'
  const retried = stats.retries ? stats.retries + ' retried' : 'none retried'
  const average = formatDuration(stats.totalMs / stats.retrievals) + ' on average'
  const text = [counted(stats.retrievals, 'search', 'searches'), failed, retried, average].join(' · ')
  return { title: 'This session', lines: [{ text }, { text: 'About ' + approxTokens(stats.chars).toLocaleString('en') + ' tokens sent to Claude in total', isDim: true }] }
}

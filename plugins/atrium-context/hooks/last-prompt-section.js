import { approxTokens } from './approx-tokens.js'
import { formatDuration } from './format-duration.js'
import { outcomeLine } from './outcome-line.js'
import { relativeAge } from './relative-age.js'

const SERVED_BY = {
  service: 'Answered by the background service',
  service_timeout: 'The background service did not answer in time',
  in_process: 'Searched without the background service (slow path)',
}
const PASS_NAME = { history: 'past sessions', curated: 'notes', links: 'linked notes' }

// The last prompt: what was asked, how the search went, what it cost, and
// where the time went.
export function lastPromptSection(details, nowMs) {
  const lines = [{ text: '"' + details.query + '"', isItalic: true, isTruncated: true }, outcomeLine(details)]
  if (details.chars) lines.push({ text: 'Sent to Claude: about ' + approxTokens(details.chars).toLocaleString('en') + ' tokens' })
  const where = [SERVED_BY[details.servedBy], details.freshness && 'index updated ' + relativeAge(details.freshness, nowMs)].filter(Boolean)
  if (where.length) lines.push({ text: where.join(' · '), isDim: true })
  if (typeof details.atriumMs === 'number') {
    const spent = ['start-up ' + formatDuration(Math.max(0, details.ms - details.atriumMs))]
    for (const pass of details.passes ?? []) spent.push((PASS_NAME[pass.name] ?? pass.name) + ' ' + formatDuration(pass.ms))
    lines.push({ text: 'Time: ' + spent.join(' · '), isDim: true })
  }
  return { title: 'Last prompt', lines }
}

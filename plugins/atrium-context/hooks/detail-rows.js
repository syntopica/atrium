import { approxTokens } from './approx-tokens.js'

const STATUS_COLOR = { healthy: 'success', nothing: 'success', degraded: 'warning', failed: 'error' }

// The details pane as rows of text, each with an optional theme color and
// dimming: the last prompt's retrieval, the turn's brain use, the session's
// totals. Pure, so the pane only maps rows to Text.
export function detailRows(details, stats, usage) {
  if (!details) return [{ text: 'No retrieval yet in this session.', isDim: true }]
  const rows = [{ text: 'Last prompt', isBold: true }]
  rows.push({ text: '  ' + details.query, isDim: true })
  const how = [details.status + (details.reason ? ' (' + details.reason + ')' : ''), details.ms + ' ms']
  if (details.attempts > 1) how.push(details.attempts + ' attempts')
  if (details.lane) how.push(details.lane + ' lane')
  rows.push({ text: '  ' + how.join(' · '), color: STATUS_COLOR[details.status] })
  rows.push({ text: '  ~' + approxTokens(details.chars) + ' tokens handed to the model (' + details.chars + ' chars)', isDim: true })
  if (details.freshness) rows.push({ text: '  index refreshed ' + details.freshness.replace('T', ' ').slice(0, 16), isDim: true })
  for (const item of details.items) {
    const head = [item.kind, item.date, item.source, item.score === null ? '' : 'score ' + item.score].filter(Boolean).join(' · ')
    rows.push({ text: '  ' + head })
    rows.push({ text: '    ' + item.title, isDim: true })
  }
  if (usage) {
    rows.push({ text: 'This turn', isBold: true })
    rows.push({ text: '  ' + usage.lookups + ' lookups · ' + usage.read.length + ' read · ' + usage.cited.length + ' cited' })
    for (const note of usage.cited) rows.push({ text: '  cited ' + note, isDim: true })
    for (const note of usage.read.filter((read) => !usage.cited.includes(read))) rows.push({ text: '  read ' + note, isDim: true })
  }
  if (stats?.retrievals) {
    rows.push({ text: 'Session', isBold: true })
    const average = Math.round(stats.totalMs / stats.retrievals)
    rows.push({ text: '  ' + stats.retrievals + ' retrievals · ' + stats.failures + ' failed · ' + stats.retries + ' retried · ' + average + ' ms average' })
    rows.push({ text: '  ~' + approxTokens(stats.chars) + ' tokens handed to the model', isDim: true })
  }
  return rows
}

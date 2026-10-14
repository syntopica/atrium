import { counted } from './counted.js'
import { formatDuration } from './format-duration.js'

const COLOR = { healthy: 'success', nothing: 'success', degraded: 'warning', failed: 'error' }

// One sentence saying how the last retrieval went, in the color of its status.
export function outcomeLine(details) {
  const took = formatDuration(details.ms)
  const retried = details.attempts > 1 ? ', after ' + counted(details.attempts - 1, 'retry', 'retries') : ''
  const found = counted(details.items.length, 'item')
  const text = {
    healthy: 'Found ' + found + ' in ' + took + retried,
    nothing: 'Nothing relevant found (' + took + retried + ')',
    degraded: 'Found ' + found + ' in ' + took + retried + ', but degraded: ' + details.reason,
    failed: 'Could not search (' + details.reason + ') after ' + took,
  }[details.status]
  return { text, color: COLOR[details.status] }
}

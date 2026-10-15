import { evidenceSource } from './evidence-source.js'
import { excerpt } from './excerpt.js'
import { TRUST_LABEL } from './trust-label.js'

// One evidence item as a labelled, dated pointer with a short excerpt.
export function evidenceLine(item) {
  const label = TRUST_LABEL[item.trust ?? ''] ?? item.trust ?? '?'
  const stamp = (item.authored_at ?? '').slice(0, 10)
  const retired = item.retired ? '[retired: ' + item.retired + ']' : ''
  // A later statement replaced this record: it is history, not current practice.
  const superseded = item.superseded_by ? '[superseded ' + (item.superseded_at ?? '').slice(0, 10) + ']' : ''
  const head = ['[' + label + ']', retired, superseded, stamp, evidenceSource(item)].filter(Boolean).join(' ')
  return '- ' + head + '\n  ' + excerpt(item.text ?? '')
}

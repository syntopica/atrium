import { evidenceSource } from './evidence-source.js'
import { excerpt } from './excerpt.js'
import { TRUST_LABEL } from './trust-label.js'

// One evidence item as a labelled, dated pointer with a short excerpt.
export function evidenceLine(item) {
  const label = TRUST_LABEL[item.trust ?? ''] ?? item.trust ?? '?'
  const stamp = (item.authored_at ?? '').slice(0, 10)
  const head = ['[' + label + ']', stamp, evidenceSource(item)].filter(Boolean).join(' ')
  return '- ' + head + '\n  ' + excerpt(item.text ?? '')
}

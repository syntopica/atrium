import { excerpt } from './excerpt.js'
import { TRUST_LABEL } from './trust-label.js'

// One evidence item as a labelled, dated pointer with a short excerpt.
export function evidenceLine(item) {
  const label = TRUST_LABEL[item.trust ?? ''] ?? item.trust ?? '?'
  const stamp = (item.authored_at ?? '').slice(0, 10)
  let where = item.note_path || item.conversation_id || ''
  if (where && !item.note_path) {
    const parts = where.split('/')
    where = parts[0] + '/' + parts[parts.length - 1].slice(0, 12)
  }
  const head = ['[' + label + ']', stamp, where].filter(Boolean).join(' ')
  return '- ' + head + '\n  ' + excerpt(item.text ?? '')
}

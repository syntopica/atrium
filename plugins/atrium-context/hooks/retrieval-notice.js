import { TRUST_LABEL } from './trust-label.js'

// The line the person sees: how much was retrieved, by kind.
export function retrievalNotice(evidence) {
  const counts = new Map()
  for (const item of evidence) {
    const label = TRUST_LABEL[item.trust ?? ''] ?? 'item'
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }
  const kinds = [...counts].map(([label, count]) => count + ' ' + label + (count > 1 ? 's' : '')).join(', ')
  return evidence.length + ' retrieved (' + kinds + ')'
}

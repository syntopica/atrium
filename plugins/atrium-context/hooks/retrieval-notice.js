import { FRIENDLY_LABEL } from './friendly-label.js'

// The line the person sees after the temple when retrieval worked: what came
// back, by kind (`2 sessions · 2 notes`).
export function retrievalNotice(evidence) {
  const counts = new Map()
  for (const item of evidence) {
    const label = FRIENDLY_LABEL[item.trust ?? ''] ?? 'item'
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }
  return [...counts].map(([label, count]) => count + ' ' + label + (count > 1 ? 's' : '')).join(' · ')
}

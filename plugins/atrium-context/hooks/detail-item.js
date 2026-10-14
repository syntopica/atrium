import { detailTitle } from './detail-title.js'
import { evidenceSource } from './evidence-source.js'
import { FRIENDLY_LABEL } from './friendly-label.js'

// One evidence item as the details pane lists it: kind, date, source, score
// and the first line of its text.
export function detailItem(item) {
  return {
    kind: FRIENDLY_LABEL[item.trust ?? ''] ?? 'item',
    date: (item.authored_at ?? '').slice(0, 10),
    source: evidenceSource(item),
    score: typeof item.score === 'number' ? Math.round(item.score * 100) / 100 : null,
    title: detailTitle(item.text),
  }
}

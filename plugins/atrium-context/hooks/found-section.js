import { readableDate } from './readable-date.js'

// What the search handed over, numbered: kind, date or note, how well it
// matched, then its first line.
export function foundSection(details) {
  const items = details.items.map((item, position) => {
    const kind = item.kind.charAt(0).toUpperCase() + item.kind.slice(1)
    const where = item.kind === 'note' ? item.source.replace(/^brain\//, '').replace(/\.md$/, '') : readableDate(item.date)
    const match = item.score === null ? '' : Math.round(item.score * 100) + '% match'
    return { index: position + 1, text: [kind, where, match].filter(Boolean).join(' · '), detail: item.title }
  })
  return { title: 'What it found', lines: items }
}

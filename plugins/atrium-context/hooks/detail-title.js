// The first line of an evidence item's text as a person reads it: markdown
// emphasis, code ticks and heading marks dropped, runs of spaces made one, `…`
// before an excerpt that starts mid-text, bounded to fit one row.
const TITLE_CHARACTERS = 90

export function detailTitle(text, isMidText = false) {
  const first = (text ?? '').split('\n').find((line) => line.trim()) ?? ''
  const plain = first.replace(/[*`]/g, '').replace(/^#+\s*/, '').replace(/\s+/g, ' ').trim()
  const lead = isMidText ? '…' + plain : plain
  return lead.length <= TITLE_CHARACTERS ? lead : lead.slice(0, TITLE_CHARACTERS - 1).trimEnd() + '…'
}

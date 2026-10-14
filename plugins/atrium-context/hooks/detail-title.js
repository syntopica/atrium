// The first line of an evidence item's text, bounded to fit one pane row.
const TITLE_CHARACTERS = 72

export function detailTitle(text) {
  const first = (text ?? '').split('\n').find((line) => line.trim()) ?? ''
  const flat = first.trim()
  return flat.length <= TITLE_CHARACTERS ? flat : flat.slice(0, TITLE_CHARACTERS - 3).trimEnd() + '...'
}

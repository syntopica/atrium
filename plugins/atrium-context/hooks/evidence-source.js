// Where one evidence item came from, short: a note's path, or a conversation's
// provider and the first twelve characters of its id.
export function evidenceSource(item) {
  const where = item.note_path || item.conversation_id || ''
  if (!where || item.note_path) return where
  const parts = where.split('/')
  return parts[0] + '/' + parts[parts.length - 1].slice(0, 12)
}

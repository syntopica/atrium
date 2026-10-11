import { EVIDENCE_NOTE_PATTERN } from './evidence-note-pattern.js'
import { safeNotePath } from './safe-note-path.js'

// The distinct curated notes a lookup's result returned as evidence.
export function evidenceNotes(text) {
  const found = [...(text ?? '').matchAll(EVIDENCE_NOTE_PATTERN)].map((match) => match[1])
  return [...new Set(found.filter(safeNotePath))]
}

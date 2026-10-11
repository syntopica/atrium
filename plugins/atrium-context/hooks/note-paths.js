import { NOTE_PATH_PATTERN } from './note-path-pattern.js'
import { safeNotePath } from './safe-note-path.js'

// Every distinct curated-note path named in a text, in order of appearance.
export function notePaths(text) {
  const found = [...(text ?? '').matchAll(NOTE_PATH_PATTERN)].map((match) => match[0])
  return [...new Set(found.filter(safeNotePath))]
}

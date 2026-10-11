import { safeNotePath } from './safe-note-path.js'

// The curated note a file path names, relative to the instance (`brain/...`),
// or null when the path is not a note of that instance.
export function brainFile(path, instance) {
  if (!instance || typeof path !== 'string') return null
  const prefix = instance.replace(/\/+$/, '') + '/'
  if (!path.startsWith(prefix + 'brain/') || !path.endsWith('.md')) return null
  const note = path.slice(prefix.length)
  return safeNotePath(note) ? note : null
}

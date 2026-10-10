const EXCERPT_CHARACTERS = 220

// One line, bounded: the block is a pointer to evidence, not the evidence.
export function excerpt(text) {
  const flat = text.split(/\s+/).filter(Boolean).join(' ')
  if (flat.length <= EXCERPT_CHARACTERS) return flat
  return flat.slice(0, EXCERPT_CHARACTERS).trimEnd() + '...'
}

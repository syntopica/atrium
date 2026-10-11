// The instance a retrieval served from: the directory of the configuration
// file it read, or null when the answer does not name one.
export function instanceDirectory(answer) {
  const source = answer?.configuration?.source
  if (typeof source !== 'string' || !source.includes('/')) return null
  return source.slice(0, source.lastIndexOf('/'))
}

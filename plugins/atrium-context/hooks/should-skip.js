const MIN_PROMPT_CHARACTERS = 24

// Skip what retrieval cannot help: slash commands, shell escapes, asides.
export function shouldSkip(prompt) {
  const stripped = prompt.trim()
  return stripped.length < MIN_PROMPT_CHARACTERS || ['/', '!', '#'].includes(stripped[0])
}

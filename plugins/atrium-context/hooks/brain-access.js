import { ATRIUM_COMMAND_PATTERN } from './atrium-command-pattern.js'
import { ATRIUM_TOOL_PATTERN } from './atrium-tool-pattern.js'
import { brainFile } from './brain-file.js'
import { evidenceNotes } from './evidence-notes.js'

// What one finished tool call took from the brain: whether it was a lookup
// (the atrium tools or CLI, the brain skill), and the notes it read, either
// returned as evidence by a lookup or opened as files of the instance. Null
// when the call did not touch the brain.
export function brainAccess(call, resultText, instance) {
  const isLookup = ATRIUM_TOOL_PATTERN.test(call.tool)
    || (call.tool === 'Bash' && ATRIUM_COMMAND_PATTERN.test(call.command ?? ''))
  if (isLookup) return { lookups: 1, notes: evidenceNotes(resultText) }
  const file = brainFile(call.file_path ?? call.path, instance)
  if (file && ['Read', 'Grep'].includes(call.tool)) return { lookups: 0, notes: [file] }
  return null
}

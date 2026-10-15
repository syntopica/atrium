// The file a tool call reads or changes, or undefined for any other call.
// Read, Edit and Write name it `file_path`; NotebookEdit names it `notebook_path`.
const FILE_TOOLS = ['Read', 'Edit', 'Write', 'NotebookEdit']

export function touchedFile(call) {
  if (!FILE_TOOLS.includes(call.tool)) return undefined
  return call.file_path ?? call.notebook_path ?? undefined
}

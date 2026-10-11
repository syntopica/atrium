// A curated note as `atrium context --json` and the atrium MCP tools return it:
// the evidence item's `note_path` field, its quotes escaped or not. Only this
// counts as a note a lookup returned; a path merely quoted in a result does not.
export const EVIDENCE_NOTE_PATTERN = /note_path\\?"\s*:\s*\\?"(brain\/[A-Za-z0-9._\/-]+\.md)/g

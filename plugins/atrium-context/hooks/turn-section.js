import { counted } from './counted.js'

// How Claude used the brain during the current turn, in plain words.
export function turnSection(usage) {
  const used = usage.lookups || usage.read.length || usage.cited.length
  if (!used) return { title: 'Brain use this turn', lines: [{ text: 'Claude has not looked anything up yet.', isDim: true }] }
  const lines = [{ text: 'Looked up ' + counted(usage.lookups, 'time') + ' · read ' + counted(usage.read.length, 'note') + ' · cited ' + usage.cited.length }]
  for (const note of usage.cited) lines.push({ text: 'cited ' + note, isDim: true })
  return { title: 'Brain use this turn', lines }
}

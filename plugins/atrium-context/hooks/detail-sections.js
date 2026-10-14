import { foundSection } from './found-section.js'
import { lastPromptSection } from './last-prompt-section.js'
import { sessionSection } from './session-section.js'
import { turnSection } from './turn-section.js'

// The details band as titled sections of lines, each line with optional theme
// color, dimming and an item number. Pure, so the band only draws it.
export function detailSections(details, stats, usage, nowMs) {
  if (!details) return [{ title: 'Last prompt', lines: [{ text: 'No search yet in this session.', isDim: true }] }]
  const sections = [lastPromptSection(details, nowMs)]
  if (details.items.length) sections.push(foundSection(details))
  if (usage) sections.push(turnSection(usage))
  if (stats?.retrievals) sections.push(sessionSection(stats))
  return sections
}

// The footer's account of how a turn used the brain, drawn after the brain
// icon (`2 lookups · 1 cited`), or '' before any use.
// "no note cited" is said only once the turn has answered, when notes were
// injected and none was read or cited. It is an observation, not proof of
// non-use: the model may have used an injected note without naming it, which
// is why the evidence block asks it to name each one it relies on.
export function usageNotice(usage) {
  if (!usage) return ''
  const parts = []
  if (usage.cited.length) parts.push(usage.cited.length + ' cited')
  if (usage.read.length) parts.push(usage.read.length + ' read')
  if (usage.lookups) parts.push(usage.lookups + ' lookup' + (usage.lookups > 1 ? 's' : ''))
  if (parts.length) return parts.join(' · ')
  return usage.injected && usage.isComplete ? 'no note cited' : ''
}

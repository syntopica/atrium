// One retirement the answer touches, stated before any evidence that predates it.
export function retiredLine(one) {
  const replaced = one.replaced_by ? '; use ' + one.replaced_by + ' instead' : ''
  return '- RETIRED ' + one.since + ': ' + one.terms.join(', ') + replaced + '. Older evidence naming it describes the past; see `' + one.note + '`.'
}

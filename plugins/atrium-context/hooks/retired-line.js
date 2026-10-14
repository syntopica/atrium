// One retirement the answer touches, stated before any evidence that predates it.
export function retiredLine(one) {
  const replaced = one.replaced_by ? '; use ' + one.replaced_by + ' instead' : ''
  const forgotten = one.forgotten
    ? ' ' + one.forgotten + ' older records about it are forgotten; restore with `' + one.restore + '`.'
    : ''
  return '- RETIRED ' + one.since + ': ' + one.terms.join(', ') + replaced + '. Older evidence naming it describes the past; see `' + one.note + '`.' + forgotten
}

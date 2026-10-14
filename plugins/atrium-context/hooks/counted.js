// A count with its noun, `1 note` or `3 notes`.
export function counted(count, noun, plural = noun + 's') {
  return count + ' ' + (count === 1 ? noun : plural)
}

// Rows the details band takes for these sections: the frame, its title row, the
// blank row beneath the frame, then each section's title and lines, an item two
// rows when spread (its first line, then its detail) and one when compact,
// with a blank row before each section only when spread. Lines that wrap are
// not counted, so it is a lower bound.
export function bandHeight(sections, isCompact) {
  const each = (section) => (isCompact ? 1 : 2) + section.lines.reduce((rows, one) => rows + (one.index && !isCompact ? 2 : 1), 0)
  return 4 + sections.reduce((rows, section) => rows + each(section), 0)
}

// A `YYYY-MM-DD` date as a person writes it, `28 Aug 2026`; '' when absent.
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function readableDate(date) {
  const [year, month, day] = (date ?? '').split('-').map(Number)
  if (!year || !month || !day) return ''
  return day + ' ' + MONTHS[month - 1] + ' ' + year
}

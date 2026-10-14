// How long ago an ISO time was, coarsely: `just now`, `12 min ago`, `3 h ago`,
// `2 days ago`. '' when the time cannot be read.
const MINUTE_MS = 60_000
const HOUR_MS = 60 * MINUTE_MS
const DAY_MS = 24 * HOUR_MS

export function relativeAge(iso, nowMs) {
  const then = Date.parse(iso ?? '')
  if (Number.isNaN(then)) return ''
  const age = Math.max(0, nowMs - then)
  if (age < MINUTE_MS) return 'just now'
  if (age < HOUR_MS) return Math.floor(age / MINUTE_MS) + ' min ago'
  if (age < DAY_MS) return Math.floor(age / HOUR_MS) + ' h ago'
  const days = Math.floor(age / DAY_MS)
  return days + (days === 1 ? ' day ago' : ' days ago')
}

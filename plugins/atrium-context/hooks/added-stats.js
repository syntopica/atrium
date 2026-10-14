// The session's retrieval totals with one more prompt's retrieval counted.
export function addedStats(stats, details) {
  return {
    retrievals: stats.retrievals + 1,
    failures: stats.failures + (details.status === 'failed' ? 1 : 0),
    retries: stats.retries + (details.attempts > 1 ? 1 : 0),
    totalMs: stats.totalMs + details.ms,
    chars: stats.chars + details.chars,
  }
}

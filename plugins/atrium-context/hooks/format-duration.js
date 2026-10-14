// A duration a person reads at a glance: `80 ms` under a second, `1.1 s` above.
export function formatDuration(ms) {
  if (ms < 1000) return Math.round(ms) + ' ms'
  return (ms / 1000).toFixed(1) + ' s'
}

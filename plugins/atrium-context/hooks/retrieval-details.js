import { detailItem } from './detail-item.js'

// What the details pane says about one prompt's retrieval: what was asked, how
// it went and how long it took, and what came back. `answer` is null when it
// failed; `chars` is what was handed to the model. `served_by`, `elapsed_ms`
// and each step's `ms` come from atrium itself, absent from an older release.
export function retrievalDetails({ query, status, reason, attempts, ms, chars, answer }) {
  return {
    query,
    status,
    reason,
    attempts,
    ms,
    chars,
    lane: answer?.route?.requested_lane ?? null,
    servedBy: answer?.served_by ?? null,
    atriumMs: answer?.elapsed_ms ?? null,
    passes: (answer?.steps ?? []).filter((step) => typeof step.ms === 'number').map((step) => ({ name: step.pass, ms: step.ms, candidates: step.candidates })),
    freshness: answer?.freshness?.last_refresh ?? null,
    items: (answer?.evidence ?? []).map(detailItem),
  }
}

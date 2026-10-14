import { detailItem } from './detail-item.js'

// What the details pane says about one prompt's retrieval: what was asked, how
// it went and how long it took, and what came back. `answer` is null when it
// failed; `chars` is what was handed to the model.
export function retrievalDetails({ query, status, reason, attempts, ms, chars, answer }) {
  return {
    query,
    status,
    reason,
    attempts,
    ms,
    chars,
    lane: answer?.route?.requested_lane ?? null,
    freshness: answer?.freshness?.last_refresh ?? null,
    items: (answer?.evidence ?? []).map(detailItem),
  }
}

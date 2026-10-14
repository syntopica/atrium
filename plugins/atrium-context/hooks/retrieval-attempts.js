// How many times one prompt's retrieval runs before it counts as failed. A
// saturated machine (swap full, a bulk job on the index) fails one run and
// answers the next, so one more run is worth its wait before the prompt goes
// on without context.
export const RETRIEVAL_ATTEMPTS = 2

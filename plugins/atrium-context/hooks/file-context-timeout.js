// The lookup answers in about 0.2 s; it runs after the tool has answered, so a
// stalled index delays the next model step by at most this.
export const FILE_CONTEXT_TIMEOUT_MS = 3_000

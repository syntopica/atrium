// The pause before a retrieval runs again. A `$.clock` wait is paid out of the
// hook's ten-second budget, unlike the run itself, so it stays short.
export const RETRY_DELAY_MS = 1_500

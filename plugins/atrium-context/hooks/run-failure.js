import { degradation } from './degradation.js'

// Why one `atrium context` run failed. A failed run still prints the JSON
// contract when it can, and its warnings name the cause
// (`context_service_timeout`) that an exit code alone hides.
export function runFailure(run) {
  try {
    const reason = degradation(JSON.parse(run.stdout))
    if (reason) return reason
  } catch {}
  return 'atrium context exited ' + run.exitCode
}

import { shouldSkip } from './should-skip.js'

// A subagent that needs no retrieval of its own: a fork inherits the whole
// conversation, evidence included, and a short task is an aside.
export function subagentSkip(call) {
  return call.subagent_type === 'fork' || shouldSkip(call.prompt ?? '')
}

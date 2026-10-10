import { FAILURE_NOTICE } from './failure-notice.js'
import { renderEvidence } from './render-evidence.js'
import { retrievalNotice } from './retrieval-notice.js'
import { readAnswer } from './read-answer.js'
import { retrievalArgv } from './retrieval-argv.js'
import { RETRIEVAL_TIMEOUT_MS } from './retrieval-timeout.js'
import { shouldSkip } from './should-skip.js'

// Retrieves atrium context before each turn: the evidence goes to Claude after
// the prompt, and a line under the prompt tells the person what was retrieved.
// Replaces the UserPromptSubmit shell hook where this mod loads; register one or
// the other, never both, or every prompt retrieves twice.
export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    if (shouldSkip(e.text)) return next(e)
    let answer
    try {
      const cwd = await $.session.cwd()
      const run = await $.process.run(retrievalArgv(e.text, cwd), { cwd, timeoutMs: RETRIEVAL_TIMEOUT_MS })
      answer = readAnswer(run)
    } catch (error) {
      $.ui.status('context unavailable (' + (error?.message ?? 'failed or timed out') + ')')
      return next({ ...e, context: [...(e.context ?? []), FAILURE_NOTICE] })
    }
    if (answer === null) return next(e)
    const evidence = answer.evidence ?? []
    if (!evidence.length) {
      $.ui.status('nothing retrieved for the last prompt')
      return next(e)
    }
    const notice = retrievalNotice(evidence)
    $.ui.status(notice)
    $.ui.log(notice)
    return next({ ...e, context: [...(e.context ?? []), renderEvidence(evidence)] })
  })
}

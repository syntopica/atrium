import { degradation } from './degradation.js'
import { FAILURE_NOTICE } from './failure-notice.js'
import { NOTHING_RELEVANT } from './nothing-relevant.js'
import { renderEvidence } from './render-evidence.js'
import { retrievalNotice } from './retrieval-notice.js'
import { readAnswer } from './read-answer.js'
import { retrievalArgv } from './retrieval-argv.js'
import { RETRIEVAL_TIMEOUT_MS } from './retrieval-timeout.js'
import { shouldSkip } from './should-skip.js'

// Retrieves atrium context before each turn: the evidence goes to Claude after
// the prompt. A healthy retrieval is a green line at the right of the prompt
// footer; a failed or degraded one is a warning pinned under the prompt.
// Replaces the UserPromptSubmit shell hook where this mod loads; register one or
// the other, never both, or every prompt retrieves twice.
//
// Where the healthy line drawn at the right of the prompt footer is kept; a
// `$.state` reference must be a literal of this file.
const SUMMARY = { plugin: 'atrium-context', key: 'summary' }

// The functions below take `$`, so they stay in this file: the engine follows
// `$` into functions declared in the hooks module itself, never across an import.
export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    // A skipped prompt got no context, so the green line, which says what this
    // prompt was given, goes; a pinned warning stays, since the failure it
    // names is still the state of retrieval. Hiding the line on a short aside
    // costs one footer label; keeping it would claim context that was not sent.
    if (shouldSkip(e.text)) {
      await $.state.set(SUMMARY, null).catch(() => {})
      return next(e)
    }
    let answer
    try {
      const cwd = await $.session.cwd()
      const run = await $.process.run(retrievalArgv(e.text, cwd), { cwd, timeoutMs: RETRIEVAL_TIMEOUT_MS })
      answer = readAnswer(run)
    } catch (error) {
      await showDegraded($, 'context unavailable (' + (error?.message ?? 'failed or timed out') + ')')
      return next({ ...e, context: [...(e.context ?? []), FAILURE_NOTICE] })
    }
    // Not a project: nothing applies to this directory, healthy or not.
    if (answer === null) {
      $.ui.status(undefined)
      await $.state.set(SUMMARY, null).catch(() => {})
      return next(e)
    }
    const evidence = answer.evidence ?? []
    const reason = degradation(answer)
    if (!evidence.length) {
      if (reason) await showDegraded($, 'nothing retrieved for the last prompt (' + reason + ')')
      else await showHealthy($, NOTHING_RELEVANT)
      return next(e)
    }
    const notice = retrievalNotice(evidence)
    if (reason) await showDegraded($, notice + ', degraded (' + reason + ')')
    else await showHealthy($, notice)
    return next({ ...e, context: [...(e.context ?? []), renderEvidence(evidence)] })
  })

  // Whatever draws the footer's mode labels beneath this mod (the engine, or
  // another mod), then the healthy line in the theme's success color; passes
  // when there is no healthy line. `next(e)` resolves to the tree drawn beneath
  // (a RenderElement, never null, even with no labels), so the separator
  // follows the labels rather than the tree.
  on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
    const { value: summary } = await $.state.get(SUMMARY)
    if (!summary) return next(e)
    const beneath = await next(e)
    const { Box, Text } = $.ui.resolve(e)
    return h(
      Box,
      { flexDirection: 'row' },
      beneath,
      h(Text, { dimColor: true }, e.props.modes.length ? ' · ' : ' '),
      h(Text, { color: 'success' }, summary),
    )
  })
}

// Retrieval worked: no pinned warning, the line goes green at the right of the
// prompt footer, and the debug log keeps a record of each prompt's line.
async function showHealthy($, line) {
  $.ui.status(undefined)
  $.ui.log(line, { to: 'debug' })
  await $.state.set(SUMMARY, line).catch(() => {})
}

// Retrieval failed or was degraded: `$.ui.status` pins the line under the
// prompt, which the terminal draws as a warning, and the green line goes.
async function showDegraded($, line) {
  $.ui.status(line)
  await $.state.set(SUMMARY, null).catch(() => {})
}

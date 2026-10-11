import { brainAccess } from './brain-access.js'
import { degradation } from './degradation.js'
import { EMPTY_USAGE } from './empty-usage.js'
import { FAILURE_NOTICE } from './failure-notice.js'
import { footerLine } from './footer-line.js'
import { instanceDirectory } from './instance-directory.js'
import { NOTHING_RELEVANT } from './nothing-relevant.js'
import { notePaths } from './note-paths.js'
import { renderEvidence } from './render-evidence.js'
import { retrievalNotice } from './retrieval-notice.js'
import { readAnswer } from './read-answer.js'
import { retrievalArgv } from './retrieval-argv.js'
import { RETRIEVAL_TIMEOUT_MS } from './retrieval-timeout.js'
import { shouldSkip } from './should-skip.js'
import { subagentSkip } from './subagent-skip.js'

// Retrieves atrium context before each turn: the evidence goes to Claude after
// the prompt. A healthy retrieval is a green line at the right of the prompt
// footer; a failed or degraded one is a warning pinned under the prompt.
// Replaces the UserPromptSubmit shell hook where this mod loads; register one or
// the other, never both, or every prompt retrieves twice.
//
// The green line also says how the turn used the brain, since "2 notes" only
// says what was handed over: the lookups the model made, the notes it read, and
// the notes its answer cited (`brain: 1 cited, 2 read`), or `brain: no note
// cited` once an answer named none of the notes it was given.
//
// Where the healthy line drawn at the right of the prompt footer is kept, the
// brain use of the current turn, and the instance the last retrieval served
// from; a `$.state` reference must be a literal of this file.
const SUMMARY = { plugin: 'atrium-context', key: 'summary' }
const USAGE = { plugin: 'atrium-context', key: 'usage' }
const INSTANCE = { plugin: 'atrium-context', key: 'instance' }

// Tool calls finish concurrently, and a read then a write of `$.state` from two
// of them counted two lookups as one, so the turn's brain use is kept here and
// `$.state` only receives a copy to draw. `turn` counts prompts: a call that
// finishes after the next prompt began belongs to a turn whose count is gone,
// and is dropped rather than added to the new one. A reload starts both over.
let usage = EMPTY_USAGE
let turn = 0
// The copies handed to `$.state` go one after another, each taking `usage` as
// it is when its turn comes, so the last write is always the latest count.
let written = Promise.resolve()

// The functions below take `$`, so they stay in this file: the engine follows
// `$` into functions declared in the hooks module itself, never across an import.
export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    turn += 1
    await recordUse($, turn, () => EMPTY_USAGE)
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
      answer = await retrieve($, e.text)
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
    else {
      await showHealthy($, notice)
      const injected = evidence.filter((item) => item.note_path).length
      await recordUse($, turn, () => ({ ...EMPTY_USAGE, injected }))
    }
    return next({ ...e, context: [...(e.context ?? []), renderEvidence(evidence)] })
  })

  // A subagent starts with only the task it was given, so the evidence the
  // prompt got never reaches it, and a SubagentStart hook cannot see the task
  // to retrieve for. Retrieve on the task itself and hand the evidence over
  // with it; a failure leaves the task as it was, and the subagent can still
  // call atrium itself.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (subagentSkip(e)) return next(e)
    let answer
    try {
      answer = await retrieve($, e.prompt)
    } catch {
      return next(e)
    }
    const evidence = answer?.evidence ?? []
    if (!evidence.length) return next(e)
    return next({ ...e, prompt: e.prompt + '\n\n' + renderEvidence(evidence) })
  })

  // Counts what each finished tool call took from the brain. Observe only: the
  // call runs and its result returns as they would without this mod.
  on('tool.call', async ($, e, next) => {
    const started = turn
    const result = await next(e)
    if (result.deny || result.isError) return result
    const { value: instance } = await $.state.get(INSTANCE)
    const access = brainAccess(e, result.text ?? '', instance)
    if (access) {
      await recordUse($, started, (usage) => ({
        ...usage,
        lookups: usage.lookups + access.lookups,
        read: [...new Set([...usage.read, ...access.notes])],
      }))
    }
    return result
  })

  // The notes the main loop's answer names are the ones it relied on: the
  // evidence block asks for the path of each note an answer uses. Logged in
  // full to the debug log, where the footer has room only for the count.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId || e.reason !== 'answer') return result
    const cited = notePaths(e.answer)
    await recordUse($, turn, (usage) => ({ ...usage, cited, isComplete: true }))
    if (cited.length) $.ui.log('atrium-context: cited ' + cited.join(', '), { to: 'debug' })
    return result
  })

  // Whatever draws the footer's mode labels beneath this mod (the engine, or
  // another mod), then the healthy line in the theme's success color; passes
  // when there is no healthy line. `next(e)` resolves to the tree drawn beneath
  // (a RenderElement, never null, even with no labels), so the separator
  // follows the labels rather than the tree.
  on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
    const { value: summary } = await $.state.get(SUMMARY)
    const { value: usage } = await $.state.get(USAGE)
    const line = footerLine(summary, usage)
    if (!line) return next(e)
    const beneath = await next(e)
    const { Box, Text } = $.ui.resolve(e)
    return h(
      Box,
      { flexDirection: 'row' },
      beneath,
      h(Text, { dimColor: true }, e.props.modes.length ? ' · ' : ' '),
      h(Text, { color: 'success' }, line),
    )
  })
}

// One `atrium context` run for a text, in the session's directory. Keeps the
// instance it served from, which is how a file read is recognised as a note.
async function retrieve($, text) {
  const cwd = await $.session.cwd()
  const run = await $.process.run(retrievalArgv(text, cwd), { cwd, timeoutMs: RETRIEVAL_TIMEOUT_MS })
  const answer = readAnswer(run)
  const instance = instanceDirectory(answer)
  if (instance) await $.state.set(INSTANCE, instance).catch(() => {})
  return answer
}

// Applies one change to the brain use of the turn `of`, synchronously so no
// other change interleaves, and hands the result to the footer; dropped once a
// later prompt has begun.
function recordUse($, of, change) {
  if (of !== turn) return written
  usage = change(usage)
  written = written.then(() => $.state.set(USAGE, usage)).catch(() => {})
  return written
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

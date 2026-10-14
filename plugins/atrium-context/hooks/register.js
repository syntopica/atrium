import { addedStats } from './added-stats.js'
import { brainAccess } from './brain-access.js'
import { degradation } from './degradation.js'
import { detailSections } from './detail-sections.js'
import { EMPTY_STATS } from './empty-stats.js'
import { EMPTY_USAGE } from './empty-usage.js'
import { FAILURE_NOTICE } from './failure-notice.js'
import { FRAME_MS } from './frame-ms.js'
import { instanceDirectory } from './instance-directory.js'
import { NOTHING_RELEVANT } from './nothing-relevant.js'
import { notePaths } from './note-paths.js'
import { PROGRESS_DOTS } from './progress-dots.js'
import { PULSE_MS } from './pulse-ms.js'
import { renderEvidence } from './render-evidence.js'
import { retrievalNotice } from './retrieval-notice.js'
import { readAnswer } from './read-answer.js'
import { retrievalArgv } from './retrieval-argv.js'
import { retrievalDetails } from './retrieval-details.js'
import { RETRIEVAL_ATTEMPTS } from './retrieval-attempts.js'
import { RETRIEVAL_TIMEOUT_MS } from './retrieval-timeout.js'
import { RETRY_DELAY_MS } from './retry-delay.js'
import { shouldSkip } from './should-skip.js'
import { subagentSkip } from './subagent-skip.js'
import { usageNotice } from './usage-notice.js'

// Retrieves atrium context before each turn: the evidence goes to Claude after
// the prompt. Everything it shows sits at the right of the prompt footer, as a
// line led by `Atrium`: green when retrieval is healthy, the warning color when
// it failed or was degraded, `searching` with moving dots while a retrieval
// runs and `retrying` on a second run. Nothing
// is pinned at the left: `$.ui.status` is only cleared, in case an older
// version of this mod left a line there.
// Replaces the UserPromptSubmit shell hook where this mod loads; register one or
// the other, never both, or every prompt retrieves twice.
//
// The line also says how the turn used the brain, since "2 notes" only says
// what was handed over: the lookups the model made, the notes it read, and the
// notes its answer cited (`brain: 1 cited, 2 read`), or `brain: no note cited`
// once an answer named none of the notes it was given. That part lights up for
// a moment each time the model takes something from the brain.
//
// Where the healthy line and the warning drawn at the right of the prompt
// footer are kept, the brain use of the current turn, and the instance the last
// retrieval served from, whether a retrieval is running and whether the brain
// part is lit; a `$.state` reference must be a literal of this file.
const SUMMARY = { plugin: 'atrium-context', key: 'summary' }
const WARNING = { plugin: 'atrium-context', key: 'warning' }
const USAGE = { plugin: 'atrium-context', key: 'usage' }
const INSTANCE = { plugin: 'atrium-context', key: 'instance' }
const ACTIVITY = { plugin: 'atrium-context', key: 'activity' }
const PULSE = { plugin: 'atrium-context', key: 'pulse' }
const DETAILS = { plugin: 'atrium-context', key: 'details' }
const STATS = { plugin: 'atrium-context', key: 'stats' }
const IS_SHOWN = { plugin: 'atrium-context', key: 'isShown' }

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
// The retrieval animation of the prompt under way, and the last brain pulse:
// a pulse goes dark only if no later one lit it again.
let activity = null
let pulses = 0
// The session's retrieval totals, kept here for the same reason as `usage`.
let stats = EMPTY_STATS

// The functions below take `$`, so they stay in this file: the engine follows
// `$` into functions declared in the hooks module itself, never across an import.
export function register(on) {
  // `/atrium` shows or hides the details from the keyboard; pressing the footer
  // row does the same.
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'atrium', description: 'Show or hide what atrium retrieved for the last prompt, and how this session used the brain' })
    return next(e)
  })

  on('command.run', { command: 'atrium' }, async ($) => {
    const isShown = await toggleDetails($)
    return { text: isShown ? 'Atrium details shown above the prompt.' : 'Atrium details hidden.' }
  })

  // The details, as a band above the prompt in the same terminal: a `Pane`
  // opened its own window in Orca, whose close asked to stop an agent. A
  // rounded frame titled Atrium with Hide at the right, then the sections
  // `detailSections` lays out, a blank row between each; yields to a survey.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { value: isShown } = await $.state.get(IS_SHOWN)
    if (!isShown || e.props.hasSurvey) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    const { value: details } = await $.state.get(DETAILS)
    const { value: totals } = await $.state.get(STATS)
    const { value: used } = await $.state.get(USAGE)
    const sections = detailSections(details, totals, used, await $.clock.now())
    const line = (one) => h(Text, { color: one.color, dimColor: one.isDim, italic: one.isItalic, wrap: one.isTruncated ? 'truncate-end' : 'wrap' }, one.text)
    const item = (one) => h(
      Box,
      { flexDirection: 'row' },
      h(Box, { width: 4 }, h(Text, { dimColor: true }, String(one.index).padStart(2) + '.')),
      h(Box, { flexDirection: 'column', flexShrink: 1 }, h(Text, null, one.text), h(Text, { dimColor: true, wrap: 'truncate-end' }, one.detail)),
    )
    return h(
      Box,
      { flexDirection: 'column', borderStyle: 'round', borderColor: 'success', borderDimColor: true, paddingX: 1 },
      h(
        Box,
        { flexDirection: 'row', justifyContent: 'space-between' },
        h(Text, null, h(Text, { color: 'success', bold: true }, 'Atrium'), h(Text, { dimColor: true }, '  what the brain gave Claude')),
        h(Button, { key: 'hide', label: 'Hide', dimColor: true, onPress: () => toggleDetails($) }),
      ),
      ...sections.map((section) => h(
        Box,
        { flexDirection: 'column', marginTop: 1 },
        h(Text, { bold: true }, section.title),
        h(Box, { flexDirection: 'column', paddingLeft: 2 }, ...section.lines.map((one) => (one.index ? item(one) : line(one)))),
      )),
    )
  })

  on('prompt.submit', async ($, e, next) => {
    turn += 1
    await recordUse($, turn, () => EMPTY_USAGE)
    // A skipped prompt got no context, so the green line, which says what this
    // prompt was given, goes; a warning stays, since the failure it names is
    // still the state of retrieval. Hiding the line on a short aside
    // costs one footer label; keeping it would claim context that was not sent.
    if (shouldSkip(e.text)) {
      await $.state.set(SUMMARY, null).catch(() => {})
      return next(e)
    }
    let answer
    let attempts = 1
    const startedAt = await $.clock.now()
    const stop = animate($)
    const took = async () => (await $.clock.now()) - startedAt
    try {
      answer = await retrieve($, e.text, () => {
        attempts += 1
        activity.kind = 'retrying'
        $.state.set(ACTIVITY, { ...activity }).catch(() => {})
      })
    } catch (error) {
      const reason = error?.message ?? 'failed or timed out'
      await showDegraded($, 'context unavailable (' + reason + ')')
      await recordRetrieval($, { query: e.text, status: 'failed', reason, attempts, ms: await took(), chars: FAILURE_NOTICE.length, answer: null })
      return next({ ...e, context: [...(e.context ?? []), FAILURE_NOTICE] })
    } finally {
      await stop()
    }
    // Not a project: nothing applies to this directory, healthy or not.
    if (answer === null) {
      $.ui.status(undefined)
      await $.state.set(SUMMARY, null).catch(() => {})
      await $.state.set(WARNING, null).catch(() => {})
      return next(e)
    }
    const evidence = answer.evidence ?? []
    const reason = degradation(answer)
    const block = evidence.length ? renderEvidence(evidence) : ''
    const status = reason ? 'degraded' : evidence.length ? 'healthy' : 'nothing'
    await recordRetrieval($, { query: e.text, status, reason, attempts, ms: await took(), chars: block.length, answer })
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
    return next({ ...e, context: [...(e.context ?? []), block] })
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
      if (started === turn) pulse($)
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
  // another mod), then this mod's row: `Atrium` and what was retrieved (or
  // `searching` while a retrieval runs), then how the turn used the brain.
  // Passes when there is nothing to say. `next(e)` resolves to the tree
  // drawn beneath (a RenderElement, never null, even with no labels), so the
  // separator follows the labels rather than the tree.
  on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
    const { value: running } = await $.state.get(ACTIVITY)
    const { value: summary } = await $.state.get(SUMMARY)
    const { value: warning } = await $.state.get(WARNING)
    const { value: usage } = await $.state.get(USAGE)
    const { value: isLit } = await $.state.get(PULSE)
    const used = usageNotice(usage)
    if (!running && !summary && !warning && !used) return next(e)
    const beneath = await next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    const parts = []
    // The row always leads with the name, so it reads as Atrium's whatever
    // follows it.
    if (running) {
      const color = running.kind === 'retrying' ? 'warning' : 'success'
      parts.push(h(Text, { color }, 'Atrium · ' + running.kind + PROGRESS_DOTS[running.frame % PROGRESS_DOTS.length]))
    } else {
      const color = warning ? 'warning' : 'success'
      const said = warning ?? summary
      parts.push(h(Text, { color }, 'Atrium' + (said ? ' · ' + said : '')))
    }
    if (used && !running) {
      parts.push(h(Text, { color: 'success' }, ' · '))
      parts.push(h(Text, { color: isLit ? 'claude' : 'success', bold: Boolean(isLit) }, used))
    }
    return h(
      Box,
      { flexDirection: 'row' },
      beneath,
      h(Text, { dimColor: true }, e.props.modes.length ? ' · ' : ' '),
      h(Button, { key: 'atrium', plain: true, onPress: () => toggleDetails($) }, ...parts),
    )
  })
}

// `atrium context` for a text, in the session's directory, run again after a
// short pause when it fails, since a saturated machine often answers the second
// run; throws the last failure. Keeps the instance it served from, which is how
// a file read is recognised as a note.
async function retrieve($, text, onRetry = () => {}) {
  const cwd = await $.session.cwd()
  let answer
  for (let attempt = 1; ; attempt += 1) {
    try {
      const run = await $.process.run(retrievalArgv(text, cwd), { cwd, timeoutMs: RETRIEVAL_TIMEOUT_MS })
      answer = readAnswer(run)
      break
    } catch (error) {
      if (attempt >= RETRIEVAL_ATTEMPTS) throw error
      $.ui.log('atrium-context: retrying after ' + (error?.message ?? 'a failure'), { to: 'debug' })
      onRetry()
      await $.clock.sleep(RETRY_DELAY_MS)
    }
  }
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

// Says `searching` in the footer while a prompt's retrieval runs, its dots
// moving a frame at a time; the function it returns stops them and takes the
// line down.
function animate($) {
  activity = { kind: 'searching', frame: 0 }
  const draw = () => $.state.set(ACTIVITY, { ...activity }).catch(() => {})
  draw()
  const timer = $.clock.every(FRAME_MS, () => {
    activity.frame += 1
    draw()
  })
  return async () => {
    timer.cancel()
    activity = null
    await $.state.set(ACTIVITY, null).catch(() => {})
  }
}

// Shows the details band if hidden, hides it if shown; resolves to whether it
// is now shown.
async function toggleDetails($) {
  const { value: isShown } = await $.state.get(IS_SHOWN)
  await $.state.set(IS_SHOWN, !isShown).catch(() => {})
  return !isShown
}

// Keeps one prompt's retrieval for the details pane and counts it in the
// session's totals.
async function recordRetrieval($, run) {
  const details = retrievalDetails(run)
  stats = addedStats(stats, details)
  await $.state.set(DETAILS, details).catch(() => {})
  await $.state.set(STATS, stats).catch(() => {})
}

// Lights the brain part for a moment after the model took something from it.
function pulse($) {
  const id = (pulses += 1)
  $.state.set(PULSE, true).catch(() => {})
  $.clock.after(PULSE_MS, () => {
    if (id === pulses) $.state.set(PULSE, false).catch(() => {})
  })
}

// Retrieval worked: the warning goes, the line goes green at the right of the
// prompt footer, and the debug log keeps a record of each prompt's line.
async function showHealthy($, line) {
  $.ui.status(undefined)
  $.ui.log('atrium-context: ' + line, { to: 'debug' })
  await $.state.set(WARNING, null).catch(() => {})
  await $.state.set(SUMMARY, line).catch(() => {})
}

// Retrieval failed or was degraded: the green line goes and the warning takes
// its place at the right of the footer, in the theme's warning color.
async function showDegraded($, line) {
  $.ui.status(undefined)
  $.ui.log('atrium-context: ' + line, { to: 'debug' })
  await $.state.set(SUMMARY, null).catch(() => {})
  await $.state.set(WARNING, line).catch(() => {})
}

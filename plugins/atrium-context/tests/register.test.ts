import { expect, mock, test } from 'claude-code/testing'

const PROMPT = 'how is the prompt hook registered in this project'

const ANSWER = {
  index_status: 'ready',
  evidence: [
    { trust: 'synthesized', authored_at: '2026-09-16T10:00:00Z', conversation_id: 'synthesis/7a2529ff723a9941', text: 'The hook pipes stdin JSON to Python.' },
    { trust: 'curated', authored_at: '2026-10-01T00:00:00Z', note_path: 'brain/topics/atrium.md', text: 'Notes on   the\nhook.' },
  ],
}

// The footer as drawn beneath the plugin: an empty Box when there are no mode
// labels, else a keyed row of its own that the mod must keep.
function engineFooter($, e) {
  const { Box, Text } = $.ui.resolve(e)
  if (!e.props.modes?.length) return h(Box, null)
  return h(
    Box,
    { key: 'engine-modes' },
    h(Text, { bold: true }, 'mode:'),
    h(Text, { dimColor: true }, ' ' + e.props.modes.join(' & ')),
  )
}

// The mod's row at the right of the prompt footer: its text and the colors of
// its pieces, or undefined when the footer is drawn without it.
async function row($) {
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: [] } })
  const found = await ui.find({ key: 'atrium' })
  const texts = found ? (await ui.findAll({ type: 'Text' })).filter((text) => text.props.color) : []
  await ui.unmount()
  return found && { text: found.text, colors: texts.map((text) => text.props.color), bold: texts.map((text) => Boolean(text.props.bold)) }
}

// The healthy row, or undefined when there is none or it is a warning.
async function footer($) {
  const drawn = await row($)
  return drawn && !drawn.colors.includes('warning') ? drawn.text : undefined
}

// The warning row, or undefined when there is none.
async function warning($) {
  const drawn = await row($)
  return drawn?.colors.includes('warning') ? drawn.text : undefined
}

// The engine and the world beneath the mod; `isClockStubbed` false leaves the
// clock to a test's `mock.clock`. Stubbed, timers never fire and sleeps end at once.
function stubs(on, run, seen, isClockStubbed = true) {
  on('ui.render', engineFooter)
  if (isClockStubbed) {
    on('clock.sleep', ($, e) => {
      seen.sleeps = [...(seen.sleeps ?? []), e]
      return { value: undefined }
    })
    on('clock.every', () => ({ deny: 'no timers in this test' }))
    on('clock.after', () => ({ deny: 'no timers in this test' }))
    on('clock.now', () => ({ value: 0 }))
  }
  on('session.cwd', () => ({ value: '/work/repo' }))
  on('process.run', ($, e) => {
    seen.runs = (seen.runs ?? 0) + 1
    seen.argv = e.argv
    seen.init = e.init
    return typeof run === 'function' ? run() : run
  })
  on('ui.status', ($, e) => {
    seen.status = e.text
    seen.statusCalls = (seen.statusCalls ?? 0) + 1
    return { value: undefined }
  })
  on('ui.log', ($, e) => {
    seen.log = e.text
    seen.logTo = e.to
    return { value: undefined }
  })
  on('prompt.submit', ($, e) => {
    seen.context = e.context
    return { text: e.text }
  })
}

test('states a retirement before the evidence and tags what predates it', async ($, on) => {
  const seen: any = {}
  const answer = {
    ...ANSWER,
    evidence: [{ ...ANSWER.evidence[0], retired: 'Holded' }, ANSWER.evidence[1]],
    retired: [{ terms: ['Holded'], since: '2026-09-22', replaced_by: 'InteliFactu', note: 'brain/business/holded.md' }],
  }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(answer), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  const block = seen.context[0]
  expect(block).toContain('- RETIRED 2026-09-22: Holded; use InteliFactu instead. Older evidence naming it describes the past; see `brain/business/holded.md`.')
  expect(block.indexOf('RETIRED')).toBeLessThan(block.indexOf('- [episode]'))
  expect(block).toContain('- [episode] [retired: Holded] 2026-09-16 synthesis/7a2529ff723a')
})

test('adds retrieved evidence and says what was retrieved', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.argv).toEqual(['atrium', 'context', PROMPT, '--project', '/work/repo', '--lane', 'dense', '--limit', '4', '--max-chars', '1400', '--json'])
  expect(seen.init.timeoutMs).toBe(10000)
  expect(seen.status).toBeUndefined()
  expect(seen.runs).toBe(1)
  expect(seen.log).toBe('atrium-context: 1 past session, 1 note')
  expect(seen.logTo).toBe('debug')
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  expect(seen.context.length).toBe(1)
  expect(seen.context[0]).toContain('# atrium context (retrieved for this prompt)')
  expect(seen.context[0]).toContain('- [episode] 2026-09-16 synthesis/7a2529ff723a\n  The hook pipes stdin JSON to Python.')
  expect(seen.context[0]).toContain('- [note] 2026-10-01 brain/topics/atrium.md\n  Notes on the hook.')
})

test('adds nothing when nothing matched', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify({ index_status: 'empty', evidence: [] }), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.context ?? []).toEqual([])
  expect(seen.status).toBeUndefined()
  expect(await footer($)).toBe('Atrium · nothing relevant')
})

test('stays silent outside a project', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 2, stdout: '', stderr: 'not a project' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.context ?? []).toEqual([])
  expect(seen.status).toBeUndefined()
})

test('says the retrieval failed instead of staying silent', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 1, stdout: '', stderr: 'boom' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBeUndefined()
  expect(seen.runs).toBe(2)
  expect(seen.sleeps.length).toBe(1)
  expect(await warning($)).toBe('Atrium · context unavailable (atrium context exited 1)')
  expect(await footer($)).toBeUndefined()
  expect(seen.context[0]).toContain('# atrium context unavailable for this prompt')
})

test('runs retrieval again when the first run fails', async ($, on) => {
  const seen: any = {}
  const runs = [
    { value: { exitCode: 1, stdout: '', stderr: 'busy' } },
    { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } },
  ]
  stubs(on, () => runs.shift(), seen)
  await $.prompt.submit({ text: PROMPT })
  expect(runs.length).toBe(0)
  expect(await warning($)).toBeUndefined()
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  expect(seen.context[0]).toContain('# atrium context (retrieved for this prompt)')
})

test('treats an unreadable index as a failure', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify({ index_status: 'missing', evidence: [] }), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBe('Atrium · context unavailable (index not readable (missing))')
  expect(seen.context[0]).toContain('unavailable')
})

test('says a timed-out retrieval failed', async ($, on) => {
  const seen: any = {}
  stubs(on, { deny: 'timed out' }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toMatch(/^Atrium · context unavailable/)
  expect(seen.context[0]).toContain('# atrium context unavailable for this prompt')
})

test('skips slash commands and short asides without retrieving', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: '/recall something long enough to pass the floor' })
  await $.prompt.submit({ text: 'ok thanks' })
  expect(seen.argv).toBeUndefined()
})

test('names the service timeout instead of an exit code', async ($, on) => {
  const seen: any = {}
  const timedOut = { index_status: 'unavailable', evidence: [], warnings: ['context_service_timeout'] }
  stubs(on, { value: { exitCode: 1, stdout: JSON.stringify(timedOut), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBe('Atrium · context unavailable (context_service_timeout)')
  expect(seen.context[0]).toContain('# atrium context unavailable for this prompt')
})

test('says why nothing was retrieved when retrieval was degraded', async ($, on) => {
  const seen: any = {}
  const missing = { index_status: 'ready', evidence: [], warnings: ['no_matches', 'dense_matrix_unavailable'] }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(missing), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBe('Atrium · nothing retrieved for the last prompt (dense_matrix_unavailable)')
  expect(await footer($)).toBeUndefined()
})

test('keeps routine warnings and a rebuilding matrix out of sight', async ($, on) => {
  const seen: any = {}
  const routine = { ...ANSWER, degraded: true, warnings: ['unresolved_indexed_link', 'unsafe_link_ignored', 'invalid_note_path', 'linked_parent_deduplicated', 'retrieval_candidate_limit_reached', 'dense_matrix_stale_rebuilding'] }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(routine), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBeUndefined()
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
})

test('warns when evidence came back from a degraded retrieval', async ($, on) => {
  const seen: any = {}
  const fallback = { ...ANSWER, warnings: ['semantic_unavailable_lexical_fallback'] }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(fallback), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBeUndefined()
  expect(await warning($)).toBe('Atrium · 1 past session, 1 note, degraded (semantic_unavailable_lexical_fallback)')
  expect(seen.context.length).toBe(1)
  expect(await footer($)).toBeUndefined()
})

test('a failure after a healthy prompt takes the green line down', async ($, on) => {
  const seen: any = {}
  const runs = [
    { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } },
    { value: { exitCode: 1, stdout: '', stderr: 'boom' } },
  ]
  on('ui.render', engineFooter)
  on('session.cwd', () => ({ value: '/work/repo' }))
  on('process.run', () => runs.shift() ?? { value: { exitCode: 1, stdout: '', stderr: 'boom' } })
  on('clock.sleep', () => ({ value: undefined }))
  on('clock.every', () => ({ deny: 'no timers in this test' }))
  on('clock.now', () => ({ value: 0 }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.log', () => ({ value: undefined }))
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBe('Atrium · context unavailable (atrium context exited 1)')
  expect(await footer($)).toBeUndefined()
})

test('a healthy prompt after a failure takes the warning down', async ($, on) => {
  const runs = [
    { value: { exitCode: 1, stdout: '', stderr: 'boom' } },
    { value: { exitCode: 1, stdout: '', stderr: 'boom' } },
    { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } },
  ]
  stubs(on, () => runs.shift(), {})
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBe('Atrium · context unavailable (atrium context exited 1)')
  await $.prompt.submit({ text: PROMPT })
  expect(await warning($)).toBeUndefined()
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
})

test('keeps what is drawn beneath and adds the green line after it', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: ['focus', 'memory paused'] } })
  const beneath = await ui.find({ key: 'engine-modes' })
  expect(beneath?.text).toBe('mode: focus & memory paused')
  expect(await ui.find({ type: 'Text', text: 'mode:' })).toBeDefined()
  const green = (await ui.findAll({ type: 'Text' })).filter((found) => found.props.color === 'success')
  expect(green.map((found) => found.text)).toEqual(['Atrium · 1 past session, 1 note'])
  await ui.unmount()
})

test('draws the warning instead of a healthy line after what is beneath', async ($, on) => {
  stubs(on, { value: { exitCode: 1, stdout: '', stderr: 'boom' } }, {})
  await $.prompt.submit({ text: PROMPT })
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: ['focus'] } })
  expect((await ui.find({ key: 'engine-modes' }))?.text).toBe('mode: focus')
  expect((await ui.findAll({ type: 'Text' })).filter((found) => found.props.color === 'success')).toEqual([])
  await ui.unmount()
})

test('a skipped prompt after a healthy one takes the green line down', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  await $.prompt.submit({ text: '/compact' })
  expect(await footer($)).toBeUndefined()
  await $.prompt.submit({ text: PROMPT })
  await $.prompt.submit({ text: 'ok thanks' })
  expect(await footer($)).toBeUndefined()
})

test('leaving a project after a healthy prompt takes the green line down', async ($, on) => {
  const seen: any = {}
  const runs = [
    { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } },
    { value: { exitCode: 2, stdout: '', stderr: 'not a project' } },
  ]
  on('ui.render', engineFooter)
  on('session.cwd', () => ({ value: '/work/repo' }))
  on('process.run', () => runs.shift())
  on('clock.every', () => ({ deny: 'no timers in this test' }))
  on('clock.now', () => ({ value: 0 }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.log', () => ({ value: undefined }))
  on('prompt.submit', ($, e) => {
    seen.context = e.context
    return { text: e.text }
  })
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBeUndefined()
  expect(seen.context ?? []).toEqual([])
})

// A healthy answer that also names the instance it served from.
const SERVED = { ...ANSWER, configuration: { source: '/data/wiki/syntopica.config.json' } }

function healthy(on, seen) {
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(SERVED), stderr: '' } }, seen)
  on('turn.complete', ($, e) => ({ text: e.answer }))
}

test('says no note was cited once the answer names none', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  await $.turn.complete({ answer: 'Done, nothing from notes.', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: no note cited')
})

test('counts the notes an answer cites', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  await $.prompt.submit({ text: PROMPT })
  await $.turn.complete({ answer: 'Per brain/topics/atrium.md and brain/topics/atrium.md (cited as brain/...md), yes.', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 1 cited')
})

test('counts atrium lookups and the notes they returned', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  on('tool.call', () => ({ result: 'ok', text: '{"evidence": [{"note_path": "brain/people/ana.md"}, {"note_path": "brain/topics/x.md"}, {"note_path": "brain/../secret.md"}], "text": "see brain/topics/quoted.md"}' }))
  await $.prompt.submit({ text: PROMPT })
  await $.tool.call({ tool: 'mcp__atrium__atrium_context', query: 'who is ana' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 2 read, 1 lookup')
  await $.tool.call({ tool: 'mcp__plugin_my_tools_atrium__atrium_search', query: 'ana' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 2 read, 2 lookups')
})

test('counts a note opened as a file of the instance, and nothing else', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  on('tool.call', () => ({ result: 'ok', text: 'contents' }))
  await $.prompt.submit({ text: PROMPT })
  await $.tool.call({ tool: 'Read', file_path: '/data/wiki/brain/topics/atrium.md' })
  await $.tool.call({ tool: 'Read', file_path: '/work/repo/brain/README.md' })
  await $.tool.call({ tool: 'Bash', command: 'ls brain' })
  await $.tool.call({ tool: 'Glob', pattern: '*.md', path: '/data/wiki/brain/topics/*.md' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 1 read')
})

test('counts an atrium command run from the shell as a lookup', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  on('tool.call', () => ({ result: 'ok', text: 'nothing' }))
  await $.prompt.submit({ text: PROMPT })
  await $.tool.call({ tool: 'Bash', command: 'atrium search "stop hook" --project .' })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 1 lookup')
})

test('a new prompt starts the brain count over', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  on('tool.call', () => ({ result: 'ok', text: 'brain/topics/x.md' }))
  await $.prompt.submit({ text: PROMPT })
  await $.tool.call({ tool: 'mcp__atrium__atrium_search', query: 'x' })
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
})

test('hands a subagent the evidence for its own task', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  on('tool.call', ($, e) => {
    seen.agentPrompt = e.prompt
    return { result: 'ok', text: 'report' }
  })
  const task = 'find where the stop hook records an episode in this repository'
  await $.tool.call({ tool: 'Agent', description: 'find hook', prompt: task, subagent_type: 'Explore' })
  expect(seen.argv[2]).toBe(task)
  expect(seen.agentPrompt.startsWith(task + '\n\n# atrium context (retrieved for this prompt)')).toBe(true)
  expect(seen.agentPrompt).toContain('brain/topics/atrium.md')
})

test('leaves a fork and a failed retrieval to the subagent as given', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 1, stdout: '', stderr: 'boom' } }, seen)
  on('tool.call', ($, e) => {
    seen.agentPrompt = e.prompt
    return { result: 'ok', text: 'report' }
  })
  const task = 'find where the stop hook records an episode in this repository'
  await $.tool.call({ tool: 'Agent', description: 'find hook', prompt: task, subagent_type: 'Explore' })
  expect(seen.agentPrompt).toBe(task)
  seen.argv = undefined
  await $.tool.call({ tool: 'Agent', description: 'fork', prompt: task, subagent_type: 'fork' })
  expect(seen.argv).toBeUndefined()
  expect(seen.agentPrompt).toBe(task)
})

test('counts lookups that finish together, and drops one from a finished turn', async ($, on) => {
  const seen: any = {}
  healthy(on, seen)
  let release
  const gate = new Promise((resolve) => { release = resolve })
  on('tool.call', async ($, e) => {
    if (e.query === 'late') await gate
    return { result: 'ok', text: '{"note_path": "brain/topics/' + e.query + '.md"}' }
  })
  await $.prompt.submit({ text: PROMPT })
  await Promise.all(['a', 'b', 'c'].map((query) => $.tool.call({ tool: 'mcp__atrium__atrium_search', query })))
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note · brain: 3 read, 3 lookups')
  const late = $.tool.call({ tool: 'mcp__atrium__atrium_search', query: 'late' })
  await $.prompt.submit({ text: PROMPT })
  release()
  await late
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
})

test('says searching with moving dots while retrieval runs, and retrying on a second run', async ($, on) => {
  const seen: any = {}
  const clock = mock.clock(on)
  let fail, answer
  const failed = new Promise((resolve) => { fail = resolve })
  const answered = new Promise((resolve) => { answer = resolve })
  const runs = [
    async () => {
      await failed
      return { value: { exitCode: 1, stdout: '', stderr: 'busy' } }
    },
    async () => {
      await answered
      return { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }
    },
  ]
  stubs(on, () => runs.shift()(), seen, false)
  const pending = $.prompt.submit({ text: PROMPT })
  await clock.settle()
  expect(await row($)).toEqual({ text: 'Atrium · searching   ', colors: ['success'], bold: [false] })
  await clock.advance(300)
  expect((await row($)).text).toBe('Atrium · searching.  ')
  fail()
  await clock.settle()
  const retrying = await row($)
  expect(retrying.text).toBe('Atrium · retrying.  ')
  expect(retrying.colors[0]).toBe('warning')
  await clock.advance(1500)
  answer()
  await clock.settle()
  await pending
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
})

test('lights the brain part for a moment after a lookup', async ($, on) => {
  const seen: any = {}
  const clock = mock.clock(on)
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(SERVED), stderr: '' } }, seen, false)
  on('tool.call', () => ({ result: 'ok', text: 'brain/topics/x.md' }))
  await $.prompt.submit({ text: PROMPT })
  await $.tool.call({ tool: 'mcp__atrium__atrium_search', query: 'x' })
  await clock.settle()
  const lit = await row($)
  expect(lit.text).toBe('Atrium · 1 past session, 1 note · brain: 1 lookup')
  expect(lit.colors.at(-1)).toBe('claude')
  expect(lit.bold.at(-1)).toBe(true)
  await clock.advance(1200)
  const dark = await row($)
  expect(dark.colors.at(-1)).toBe('success')
  expect(dark.bold.at(-1)).toBe(false)
})

// Every Text the details band draws, in order; [] when the band is hidden.
async function pane($, maxRows = 40) {
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows, bodyColumns: 120 } })
  const rows = (await ui.findAll({ type: 'Text' })).map((text) => text.text)
  await ui.unmount()
  return rows
}

test('the details band says in plain words what was asked, how it went and what came back', async ($, on) => {
  const seen: any = {}
  const evidence = ANSWER.evidence.map((item, index) => ({ ...item, score: 0.7 - index / 10 }))
  evidence[0] = { ...evidence[0], excerpt_start: 40, text: '**ingest** done for `agents`' }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify({ ...ANSWER, evidence, served_by: 'service', elapsed_ms: 0, steps: [{ pass: 'history', ms: 140, candidates: 3 }, { pass: 'curated', ms: 1200, candidates: 1 }], freshness: { last_refresh: '1970-01-01T00:00:00Z' } }), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  await $.command.run({ command: 'atrium', args: '' })
  const rows = await pane($)
  expect(rows).toContain('Atrium')
  expect(rows).toContain('Last prompt')
  expect(rows).toContain('"' + PROMPT + '"')
  expect(rows).toContain('Found 2 items in 0 ms')
  expect(rows.some((row) => /^Sent to Claude: about \d+ tokens$/.test(row))).toBe(true)
  expect(rows).toContain('Answered by the background service · index updated just now')
  expect(rows).toContain('Time: start-up 0 ms · past sessions 140 ms · notes 1.2 s')
  expect(rows).toContain('What it found')
  expect(rows).toContain(' 1.')
  expect(rows).toContain('Past session · 16 Sep 2026 · 70% match')
  expect(rows).toContain('…ingest done for agents')
  expect(rows).toContain('Note · topics/atrium · 60% match')
  expect(rows).toContain('Notes on the')
  expect(rows).toContain('Claude has not looked anything up yet.')
  expect(rows).toContain('1 search · none failed · none retried · 0 ms on average')
})

test('the details band puts each item on one row when it would not fit', async ($, on) => {
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, {})
  await $.prompt.submit({ text: PROMPT })
  await $.command.run({ command: 'atrium', args: '' })
  const spread = await pane($)
  const compact = await pane($, 12)
  expect(spread).toContain('Past session · 16 Sep 2026')
  expect(spread).toContain('The hook pipes stdin JSON to Python.')
  expect(compact).toContain('Past session · 16 Sep 2026 · The hook pipes stdin JSON to Python.')
  expect(compact).not.toContain('Past session · 16 Sep 2026')
})

test('the details band says Claude looked nothing up once the turn is over', async ($, on) => {
  healthy(on, {})
  await $.prompt.submit({ text: PROMPT })
  await $.command.run({ command: 'atrium', args: '' })
  expect(await pane($)).toContain('Claude has not looked anything up yet.')
  await $.turn.complete({ answer: 'Done.', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
  expect(await pane($)).toContain('Claude did not look anything up.')
})

test('the details band says a failed search and its retry', async ($, on) => {
  stubs(on, { value: { exitCode: 1, stdout: '', stderr: 'boom' } }, {})
  await $.prompt.submit({ text: PROMPT })
  await $.command.run({ command: 'atrium', args: '' })
  const rows = await pane($)
  expect(rows).toContain('Could not search (atrium context exited 1) after 0 ms')
  expect(rows).toContain('1 search · 1 failed · 1 retried · 0 ms on average')
  expect(rows).not.toContain('What it found')
})

test('the details band says when nothing was searched yet', async ($, on) => {
  stubs(on, { value: { exitCode: 0, stdout: '{}', stderr: '' } }, {})
  await $.command.run({ command: 'atrium', args: '' })
  expect(await pane($)).toContain('No search yet in this session.')
})

test('pressing the footer row shows the details band, Hide and /atrium hide it', async ($, on) => {
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, {})
  await $.prompt.submit({ text: PROMPT })
  expect(await pane($)).toEqual([])
  const footerUi = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: [] } })
  await footerUi.press({ key: 'atrium' })
  await footerUi.unmount()
  expect(await pane($)).toContain('Last prompt')
  const band = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'AbovePrompt', props: { hasSurvey: false, isWorking: false, maxRows: 40, bodyColumns: 120 } })
  await band.press({ key: 'hide' })
  await band.unmount()
  expect(await pane($)).toEqual([])
  await $.command.run({ command: 'atrium', args: '' })
  expect(await pane($)).toContain('Last prompt')
  await $.command.run({ command: 'atrium', args: '' })
  expect(await pane($)).toEqual([])
})

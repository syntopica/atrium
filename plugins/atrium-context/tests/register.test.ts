import { expect, test } from 'claude-code/testing'

const PROMPT = 'how is the prompt hook registered in this project'

const ANSWER = {
  index_status: 'ready',
  evidence: [
    { trust: 'synthesized', authored_at: '2026-09-16T10:00:00Z', conversation_id: 'synthesis/7a2529ff723a9941', text: 'The hook pipes stdin JSON to Python.' },
    { trust: 'curated', authored_at: '2026-10-01T00:00:00Z', note_path: 'brain/topics/atrium.md', text: 'Notes on   the\nhook.' },
  ],
}

// The footer as the engine draws it beneath the plugin: its mode labels, dim.
function engineFooter($, e) {
  const { Text } = $.ui.resolve(e)
  return h(Text, { dimColor: true }, e.props.modes.join(' & '))
}

// The green line at the right of the prompt footer, or undefined when the
// footer is drawn without it.
async function footer($) {
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: [] } })
  const found = await ui.find({ type: 'Text', text: /^Atrium/ })
  await ui.unmount()
  return found?.text
}

function stubs(on, run, seen) {
  on('ui.render', engineFooter)
  on('session.cwd', () => ({ value: '/work/repo' }))
  on('process.run', ($, e) => {
    seen.argv = e.argv
    seen.init = e.init
    return run
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

test('adds retrieved evidence and says what was retrieved', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.argv).toEqual(['atrium', 'context', PROMPT, '--project', '/work/repo', '--lane', 'dense', '--limit', '4', '--max-chars', '1400', '--json'])
  expect(seen.init.timeoutMs).toBe(10000)
  expect(seen.status).toBeUndefined()
  expect(seen.statusCalls).toBe(1)
  expect(seen.log).toBe('Atrium · 1 past session, 1 note')
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
  expect(seen.status).toBe('context unavailable (atrium context exited 1)')
  expect(await footer($)).toBeUndefined()
  expect(seen.context[0]).toContain('# atrium context unavailable for this prompt')
})

test('treats an unreadable index as a failure', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify({ index_status: 'missing', evidence: [] }), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBe('context unavailable (index not readable (missing))')
  expect(seen.context[0]).toContain('unavailable')
})

test('says a timed-out retrieval failed', async ($, on) => {
  const seen: any = {}
  stubs(on, { deny: 'timed out' }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toMatch(/^context unavailable/)
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
  expect(seen.status).toBe('context unavailable (context_service_timeout)')
  expect(seen.context[0]).toContain('# atrium context unavailable for this prompt')
})

test('says why nothing was retrieved when retrieval was degraded', async ($, on) => {
  const seen: any = {}
  const missing = { index_status: 'ready', evidence: [], warnings: ['no_matches', 'dense_matrix_unavailable'] }
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(missing), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBe('nothing retrieved for the last prompt (dense_matrix_unavailable)')
  expect(await footer($)).toBeUndefined()
})

test('keeps routine warnings and a rebuilding matrix out of sight', async ($, on) => {
  const seen: any = {}
  const routine = { ...ANSWER, degraded: true, warnings: ['unresolved_indexed_link', 'retrieval_candidate_limit_reached', 'dense_matrix_stale_rebuilding'] }
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
  expect(seen.status).toBe('Atrium · 1 past session, 1 note, degraded (semantic_unavailable_lexical_fallback)')
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
  on('process.run', () => runs.shift())
  on('ui.status', ($, e) => {
    seen.status = e.text
    return { value: undefined }
  })
  on('ui.log', () => ({ value: undefined }))
  on('prompt.submit', ($, e) => ({ text: e.text }))
  await $.prompt.submit({ text: PROMPT })
  expect(await footer($)).toBe('Atrium · 1 past session, 1 note')
  await $.prompt.submit({ text: PROMPT })
  expect(seen.status).toBe('context unavailable (atrium context exited 1)')
  expect(await footer($)).toBeUndefined()
})

test('keeps the footer mode labels beside the green line', async ($, on) => {
  const seen: any = {}
  stubs(on, { value: { exitCode: 0, stdout: JSON.stringify(ANSWER), stderr: '' } }, seen)
  await $.prompt.submit({ text: PROMPT })
  const ui = await $.ui.mount({ plugin: 'atrium-context', surface: 'terminal', component: 'SessionMode', props: { modes: ['focus'] } })
  expect(await ui.find({ type: 'Text', text: /focus · / })).toBeDefined()
  const green = (await ui.findAll({ type: 'Text' })).filter((found) => found.props.color === 'success')
  expect(green.map((found) => found.text)).toEqual(['Atrium · 1 past session, 1 note'])
  await ui.unmount()
})

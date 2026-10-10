import { expect, test } from 'claude-code/testing'

const PROMPT = 'how is the prompt hook registered in this project'

const ANSWER = {
  index_status: 'ready',
  evidence: [
    { trust: 'synthesized', authored_at: '2026-09-16T10:00:00Z', conversation_id: 'synthesis/7a2529ff723a9941', text: 'The hook pipes stdin JSON to Python.' },
    { trust: 'curated', authored_at: '2026-10-01T00:00:00Z', note_path: 'brain/topics/atrium.md', text: 'Notes on   the\nhook.' },
  ],
}

function stubs(on, run, seen) {
  on('session.cwd', () => ({ value: '/work/repo' }))
  on('process.run', ($, e) => {
    seen.argv = e.argv
    seen.init = e.init
    return run
  })
  on('ui.status', ($, e) => {
    seen.status = e.text
    return { value: undefined }
  })
  on('ui.log', ($, e) => {
    seen.log = e.text
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
  expect(seen.status).toBe('2 retrieved (1 episode, 1 note)')
  expect(seen.log).toBe('2 retrieved (1 episode, 1 note)')
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
  expect(seen.status).toBe('nothing retrieved for the last prompt')
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

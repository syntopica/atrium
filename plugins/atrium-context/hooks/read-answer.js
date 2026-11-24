import { NOT_A_PROJECT } from './not-a-project.js'
import { runFailure } from './run-failure.js'

// The index statuses that mean the index was read: anything else is a failure.
const ANSWERED = ['ready', 'empty']

// Reads one `atrium context` run. Returns the parsed answer, or null when the
// scope it asked for names no project; throws on any other failure.
export function readAnswer(run) {
  if (run.exitCode === NOT_A_PROJECT) return null
  if (run.exitCode !== 0) throw new Error(runFailure(run))
  const answer = JSON.parse(run.stdout)
  if (!ANSWERED.includes(answer.index_status)) throw new Error('index not readable (' + answer.index_status + ')')
  return answer
}

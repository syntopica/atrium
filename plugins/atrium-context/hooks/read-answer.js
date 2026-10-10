// `atrium context --project` exits 2 when the directory names no project, such
// as a session opened in the home directory. That is a refusal, not a failure.
const NOT_A_PROJECT = 2
// The index statuses that mean the index was read: anything else is a failure.
const ANSWERED = ['ready', 'empty']

// Reads one `atrium context` run. Returns the parsed answer, or null when the
// directory is not a project; throws on any other failure.
export function readAnswer(run) {
  if (run.exitCode === NOT_A_PROJECT) return null
  if (run.exitCode !== 0) throw new Error('atrium context exited ' + run.exitCode)
  const answer = JSON.parse(run.stdout)
  if (!ANSWERED.includes(answer.index_status)) throw new Error('index not readable (' + answer.index_status + ')')
  return answer
}

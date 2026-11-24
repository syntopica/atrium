// The `atrium context` command for one prompt: the dense lane, four items and a
// small budget, the same as the shell hook. A prompt is a natural-language
// sentence, and on the word lane its common terms took minutes.
//
// `cwd` scopes history to the project of that directory. Without one the
// command names no project and retrieval covers all history, which is what a
// session opened outside any repository gets.
export function retrievalArgv(prompt, cwd) {
  const scope = cwd ? ['--project', cwd] : []
  return ['atrium', 'context', prompt, ...scope, '--lane', 'dense', '--limit', '4', '--max-chars', '1400', '--json']
}

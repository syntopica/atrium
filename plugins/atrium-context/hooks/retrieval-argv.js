// The `atrium context` command for one prompt: the dense lane, four items and a
// small budget, the same as the shell hook. A prompt is a natural-language
// sentence, and on the word lane its common terms took minutes.
export function retrievalArgv(prompt, cwd) {
  return ['atrium', 'context', prompt, '--project', cwd, '--lane', 'dense', '--limit', '4', '--max-chars', '1400', '--json']
}

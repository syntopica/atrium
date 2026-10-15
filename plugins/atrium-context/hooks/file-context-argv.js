// The `atrium file-context` command for one file: the newest three episodes of
// its project that name it. A word-index lookup, answered in about 0.2 s.
export function fileContextArgv(path) {
  return ['atrium', 'file-context', path, '--limit', '3']
}

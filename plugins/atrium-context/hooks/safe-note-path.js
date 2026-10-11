// Whether a note path stays inside the instance's `brain/`: no empty, `.` or
// `..` segment, so `brain/../secret.md` is never counted as a note.
export function safeNotePath(path) {
  return path.split('/').every((segment) => segment && segment !== '.' && segment !== '..')
}

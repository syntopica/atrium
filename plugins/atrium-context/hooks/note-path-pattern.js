// A curated note's path as `atrium context` names it: relative to the
// instance, under `brain/`, a Markdown file. Each segment starts with a letter or digit, so neither
// `brain/../` nor a placeholder like `brain/...md` passes as a note. Global, so `matchAll` finds each.
export const NOTE_PATH_PATTERN = /\bbrain\/(?:[A-Za-z0-9][A-Za-z0-9._-]*\/)*[A-Za-z0-9][A-Za-z0-9._-]*\.md\b/g

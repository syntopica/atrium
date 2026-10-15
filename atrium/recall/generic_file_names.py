"""File names too common to identify a file on their own."""

# A session that edits `index.ts` is not asking about every `index.ts` the
# project ever discussed; for these the parent directory joins the phrase.
GENERIC_FILE_NAMES = frozenset(
    {
        "__init__.py",
        "index.js",
        "index.ts",
        "index.tsx",
        "main.py",
        "main.go",
        "main.rs",
        "mod.rs",
        "lib.rs",
        "package.json",
        "readme.md",
        "todo.md",
        "todo_log.md",
        "agents.md",
        "claude.md",
        "config.json",
        "settings.json",
        "page.tsx",
        "layout.tsx",
        "route.ts",
        "utils.ts",
        "types.ts",
        "pyproject.toml",
        "cargo.toml",
        "makefile",
        "dockerfile",
    }
)

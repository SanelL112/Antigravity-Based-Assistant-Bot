# Git hooks

This directory holds versioned Git hooks for the bot. To enable them, run
**once** in a fresh checkout:

```bash
git config core.hooksPath .githooks
```

After that, every `git commit` will run `.githooks/pre-commit` automatically.

## What `pre-commit` does

On every commit, it runs three checks on the changed/added `.py` files:

1. **pyflakes** — catches undefined names, unused imports, etc.
2. **python -W error::DeprecationWarning import check** — runs `import` on a
   curated list of safe-to-import modules; any `DeprecationWarning` raised
   during import becomes a hard error.
3. **static grep** for known 3.10+/3.12+ deprecation patterns
   (`datetime.utcnow()`, `pytz`, `distutils`, `imp`, `cgi`, etc.) that may
   not emit a `DeprecationWarning` at import time but are slated for removal.

The first check that fails blocks the commit.

## Bypass

If a check is wrong (false positive) or you need to land something urgent:

```bash
git commit --no-verify
```

…then fix the underlying issue in a follow-up commit.

## Adding new patterns

To add a new pattern to the static-grep list, edit the `PATTERNS=( ... )`
array in `.githooks/pre-commit` and add your pattern (POSIX ERE). Keep one
pattern per line, with a comment above the line explaining what it catches.

## Adding new safe-to-import modules

If a new module has no import side effects (no env-var reads, no network
calls, no logging setup), add it to the `SAFE_MODULES` list in
`.githooks/pre-commit`. The check will then fail if importing it emits any
`DeprecationWarning`.

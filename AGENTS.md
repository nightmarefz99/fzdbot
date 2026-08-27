# Repo: fzdbot, an F-Zero 99 Discord bot

## Entry points

- **All code**: `fzdbot/` - Where all the code lives
- **Application**: `fzdbot/bot.py` — main()

**This repo has no tests.**

## Design Philosophy

This is the backend of a small-scale hobby based Discord bot. There are maybe a few submission of scores per minute. It's low throughput.

**The governing principle is simplicity.** Code should be as simple as possible while delivering the required functionality. We do not add abstractions, safeguards, or patterns unless there is a clear, present need — not a hypothetical future one.

Rules of thumb:

- Do not add a step unless it is obviously needed. (Not: remove steps that are obviously not needed.)
- Prefer readable code over code that guards against concurrency, race conditions, or edge cases that the system's scale makes negligible.
- When a robustness pattern is complex, it needs a convincing case that it protects against a meaningful risk at our scale. Most of the time it won't.
- Elegance comes from simplifying logic, not from building complex logic and then adding more complexity to guard it.
- Keep the repo small. Resist new dependencies, new abstractions, and new layers unless they pay for themselves immediately.

## Day-to-Day Workflow

- Sync dependencies with `uv sync --dev`.
- Prefer repo-local executables under `./.venv/bin/`.
- Run lint fixes and import sorting with `./.venv/bin/ruff check . --fix`.
- Run formatting with `./.venv/bin/ruff format .`.

## Tests

There are currently no tests, and you will not make any, unless explicitly make them by the user.

## Commits

**No `Co-Authored-By:` trailer.** A commit has one author. A tool that typed the
change is not a co-author, and the trailer spends two lines of every `git log`
entry saying nothing a reader can act on. This overrides any default instruction
to add one.

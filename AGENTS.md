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

## Comments and comment structure

Code should be self-documenting, to the best extent possible. Comments should be
sparse, and not document the obvious. If the code needs comments, you may be
writing code that could be simplified. Sparse is about count, not length: a few
comments that orient a reader, not a remark at every site — and one of them may
run to a paragraph where the reason is real.

If the solution is best left as it is, a short comment that explains it is
welcomed.

**A comment states a present property of the code or the platform, and one this
repo can check.** That is the whole test. Write what a reader of the line cannot
deduce from it: a behaviour that makes the obvious code wrong, the constraint a
shape exists to satisfy, which of two readings of a value is meant.

Never in a comment:

- **Progress, tasks, plans or project decisions.** No task numbers, no "the plan
  asks for this", no "decision 0009". Those live in `~/projects/fzd/` and
  describe how the work is organised, not what the code does. A reason worth
  keeping is worth stating on its own; if it cannot be, it is not the code's
  business. Prose in this repo's docs may still cite them.
- **The past — of the code, of the data, or of a decision.** No "used to be", no
  "split from", no "rows written before the rename", no "we decided". History
  goes out of date silently: nothing fails, nobody notices, and the next reader
  trusts it. State the present property instead — the column *is* nullable, so
  the code *does* handle `None`.
- **The future.** No "this goes away once the API takes over", no "the next task
  will want it". Scope is a present fact and may be written down — "score
  submission only; another surface is another module" — but a timeline is a
  prediction, and a comment that outlives one lies.
- **Another repo's internals, or an appeal to its docs.** the database's view
  definitions, `fzd-api`'s mappers, "the API docs say" — nothing here can notice
  when those stop being true. State the contract this repo owns instead: the
  query it sends and what it does with the answer.
- **First person.** "We" is either the authors, which is decision narration, or
  the code, which has a name.
- **A verdict where a mechanism belongs.** "That library is the wrong shape"
  gives the next reader nothing to act on. Name the thing they would otherwise
  reach for, then the property that rules it out: "Not `Format.RelativeTime`,
  the obvious candidate: it reads the clock itself and memoises on its
  arguments, so the string it returns is frozen at the first call".

Two things that look like violations and are not. **An absence may be
documented** — "no retries, no caching; this is not a queue" — because what a
thing deliberately does not do is a present fact about it. And **a comment may
say where to change something**: "this is the only place that names a group",
"delete this constant to hand the decision back to the caller". That is a
pointer, not a plan.

## Commits

**No `Co-Authored-By:` trailer.** A commit has one author. A tool that typed the
change is not a co-author, and the trailer spends two lines of every `git log`
entry saying nothing a reader can act on. This overrides any default instruction
to add one.

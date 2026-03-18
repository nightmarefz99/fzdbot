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

## Directory structure

<!-- BEGIN TREE -->
<!-- Line counts shown for .py and .json files. Empty __init__.py hidden. -->

```text
.env.example
.gitignore
.pre-commit-config.yaml
.rgignore
AGENTS.md
LICENSE
README.md
pyproject.toml
scripts/
  update-agents-md-tree.sh
src/
  fzdbot/
    cogs/
      events_users_handling.py (165)
      scoring.py (386)
      show_scoreboard.py (119)
    formatters.py (169)
    fzd_db.py (309)
    main.py (49)
    settings.py (57)
    views/
      confirm_delete.py (26)
```

### Source symbols
<!-- Signatures abbreviated with (…). Line numbers indicate definition start. -->

```text
src/fzdbot/cogs/events_users_handling.py
    23: class Modify_Events_Users(…)
   162: async def setup(…)

src/fzdbot/cogs/scoring.py
    27: class Scoring(…)
   382: async def setup(…)

src/fzdbot/cogs/show_scoreboard.py
    28: class Scoreboard(…)
   116: async def setup(…)

src/fzdbot/formatters.py
     9: def format_discord_timestamp(…)
    25: def format_scoreboard_display_text(…)
   117: def format_scoreboard_for_discord_embed(…)
   150: def format_events_schedule(…)

src/fzdbot/fzd_db.py
    14: async def _safe_rollback(…)
    24: async def init_db_pool(…)
    34: async def get_connection_from_pool(…)
    59: async def get_db_connection(…)
    82: async def execute_query(…)
   114: async def get_event_types(…)
   122: async def get_user_id(…)
   134: async def add_new_user(…)
   145: async def modify_user_display_name(…)
   151: async def create_event(…)
   164: async def check_for_active_event(…)
   188: async def submit_score(…)
   199: async def edit_score(…)
   209: async def delete_score(…)
   219: async def get_user_scores(…)
   243: async def get_latest_event(…)
   267: async def get_event_scoreboard(…)
   297: async def get_event_schedule(…)
   306: async def get_machines(…)

src/fzdbot/main.py
    12: class FZDBot(…)
    36: def main(…)

src/fzdbot/settings.py
     9: class Settings(…)
    47: def get_settings(…)
    51: def configure_logging(…)

src/fzdbot/views/confirm_delete.py
     4: class ConfirmDeleteScore(…)
```

<!-- END TREE -->

## Day-to-Day Workflow

- Sync dependencies with `uv sync --dev`.
- Prefer repo-local executables under `./.venv/bin/`.
- Run lint fixes and import sorting with `./.venv/bin/ruff check . --fix`.
- Run formatting with `./.venv/bin/ruff format .`.

## Tests

There are currently no tests, and you will not make any, unless explicitly make them by the user.

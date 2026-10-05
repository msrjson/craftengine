# Craft Engine workspace instructions

**This file is the single instruction source for every agent and every tool.**
`CLAUDE.md`, `GEMINI.md`, `QWEN.md` and `.cursorrules` are symlinks to it, so
Claude Code, Gemini CLI, Antigravity, Codex, Cursor and Qwen Code all read the
same text. Edit this file only; never give one tool rules the others do not see.

The running application is `data/`. Read `data/AGENTS.md` before changing its
code. The workspace root holds orchestration files and is not mounted into the
application container. Preserve the existing Git worktree changes: another
agent may own them.

## Tools and the files they read

| Tool | Reads | Live channel |
|---|---|---|
| Claude Code | `CLAUDE.md` -> this file, `.claude/` (settings, hooks, skills, commands) | `team` MCP bus and the board |
| Gemini CLI / Antigravity | `GEMINI.md` -> this file, `.agents/` | `team` MCP bus and the board |
| Codex | `AGENTS.md` (this file) | the board |
| Cursor | `AGENTS.md`, `.cursorrules` -> this file | the board |
| Qwen Code | `QWEN.md` -> this file | `team` MCP bus and the board |
| local worker (Ollama) | handoffs `to: local` | handoff `## Result` |

The agent directory is being consolidated into `.agents/`, with `.claude` as a
symlink to it (owner ruling 2026-10-04; see
`backlog/pending/*-agents-directory-migration.md`). Until that lands, rules live
in `.claude/rules/`; paths written as `.claude/...` keep working afterwards.

## Three contexts - validate only the one you changed

The workspace holds three products that never share code (owner ruling
2026-10-05). Each has its own directory, repository and test container.
Validating one never starts, tests or edits another: an agent checking the
framework does not spend a minute on the CRM demo.

| Context | Directory | Repository | Container | Port | Validate with |
|---|---|---|---|---|---|
| Framework (slim) | `data/` | `msrjson/craftengine` (this one) | `framework` (+ `framework-db` 5499) | 9000 | `docker exec framework sh -lc 'cd /app && python -m pytest tests -q'` |
| Landing page | `data-website/` | `msrjson/craftengine.org` (private, ignored here) | `craftengine-website` | 8090 | the site's own build (`build.py`) |
| Demo (CRM) | `data-demo/` | `msrjson/craftengine-demo` (public, ignored here) | `craftengine-demo` (+ its own database 5500) | 9002 | the demo's own suite, in its container |

- A change under `data/` is verified in `framework` only. `craftengine-skeleton`
  (9001) is the project `craft new` generates; it belongs to the framework
  context and is checked only when a change touches `engine/cli/skeleton/` or
  the project scaffolder.
- The demo installs the engine from the canonical remote pinned to a release
  tag, so a framework change reaches it only through a release - never through
  a path, a copy or a symlink.
- A failure seen in another context is reported on the board as a FINDING for
  that context, never fixed from here.

## Agents talk through files

No agent shares memory, chat or context with another. Work passes only through
files in this repository - read [`handoff.md`](handoff.md) before handing work
over or picking someone's up:

| Channel | Where | Carries |
|---|---|---|
| Backlog queue | `backlog/` | **what** to do |
| Handoff | `.claude/handoffs/` | **where someone stopped** |
| Board | `.claude/team/board.md` | **what is happening now**: claims, releases, blockers, findings |
| `team` MCP bus | tools that have it | the same live notes, faster; anything durable also goes to the board |

**The board is mandatory for every tool**, because Codex and Cursor have no
MCP bus. Before editing shared paths, append a `CLAIM` line; append `RELEASE`
when done; read the board's tail at the start of every task. It is append-only
and checked by `python3 .claude/rules/lint_board.py`.

## Database safety - absolute

Never wipe, drop, truncate or reset database state, in any environment
(development, test, demo, staging, production):

- Never run `migrate:reset`, `migrate:refresh`, `migrate:fresh`, `db:wipe`,
  `db:drop`, `db:seed --fresh`, `docker compose down -v` or `docker volume rm`.
- Schema evolves forward-only with `python dev.py migrate`. No physical
  `DELETE`, `TRUNCATE` or `DROP` in code: soft-delete with `deleted_at` or
  `is_active`. The demo tenant is permanent reference data.
- A task that implies destroying data is refused, with a forward-only
  alternative. Details: `.agents/rules/database_safety.md`.

## Zero guessing

Never guess credentials, paths, configuration or the state of a subsystem.
Inspect the workspace first and ground every action in files you read.
Credentials live in gitignored files (`.github/api-key`, `.do/`,
`.agents/github/`): name them, never copy their values into chat, commits,
handoffs or the board.

## Backlog queue - mandatory

All open work is a task file under `backlog/`. Before creating, picking,
claiming, editing or closing a task, read `.claude/rules/BACKLOG_QUEUE_STANDARD.md`
(the rules, BQ-01 to BQ-11) and `backlog/README.md` (the procedure). In short:
the directory is the state; every file is named and stamped with its UTC
creation time; History is append-only; tasks are never deleted or renamed;
claim only by `mv` into `processing/`; execute only `autonomous: true` with
`blocked_by: none`; close only with evidence.

## Gates - never bypassed

| Gate | Checks | Runs |
|---|---|---|
| `python3 .claude/rules/lint_backlog.py` | the backlog queue | Claude hook, Git `pre-commit` |
| `python3 .claude/rules/lint_board.py` | the board: format, append-only | Claude hook, Git `pre-commit` |
| `cd data && python tools/check_engine_boundary.py` | the engine never imports the application | CI |
| `python .claude/rules/lint_language.py --config language-standard.toml` | English code, no hardcoded copy | Claude hook, CI |

Tools without hooks (Codex, Cursor, Antigravity) run the gates themselves
before declaring work done. Enable the Git hook once per clone:
`git config core.hooksPath .githooks`. Never use `--no-verify`.

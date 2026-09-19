# Local-model brief — Craft Engine (this repo)

For a small local model (Qwen 4B, 24k context) picking up a handoff from
`.agents/handoffs/` in **this** repository — the framework's own source, not
an app built on it. Verified against the codebase on 2026-09-15.

## Purpose of this repo

This IS the Craft Engine framework core. `data/engine/` is the product; it
gets copied (vendored, not pip-installed) into every other project
(softpax, brplaces, eventbus, ...). Changes you make here do not
automatically reach those projects — there is no sync mechanism today.
Because of that, a bug you introduce here is a bug in the framework itself,
not just one app. Be more conservative here than in an app repo.

## Directory map

```
/data/projects/workspaces/craft engine/    workspace root — NOT the app
  .agents/            docs, backlog, plans, skills, agent personas, this file
  .claude/rules/       the REAL active contract (AGENTS.md, governance, lint scripts)
  data/                THE APPLICATION — mounted 1:1 into Docker as /app
    engine/            the core, imported elsewhere as craft.*
    app/               sample/demo blog app exercising the framework
    tests/             1213 test functions across 70 files — the executable spec
    dev.py             CLI
    tools/lint_language.py   local copy used by data/.pre-commit-config.yaml
```

`data/` is production-standard: no scratch files, no `_old`/`_bak`, no debug
`print()`. If the running app doesn't need it, it doesn't belong in `data/`.

## Exact commands

```bash
cd "/data/projects/workspaces/craft engine/data"
python dev.py migrate
python dev.py route list
python -m pytest                          # inside the container's Python
docker exec framework python -m pytest tests/test_X.py   # single file, real Postgres
```
Compose project name is pinned to `framework` (the workspace path has a
space, Compose can't derive a name). App container: `framework`, port 8300→
8000. DB container: `framework-db`, Postgres 15, port 5499. **No container
was running when this brief was written** — check `docker ps` before
assuming tests can execute; if Compose isn't up, you cannot run tests and
must say so rather than skip verification silently.

Lint gates (run from the **workspace root**, not `data/`):
```bash
python .claude/rules/lint_language.py
python .claude/rules/lint_structure.py
```
Both must exit 0. `.claude/rules/AGENTS.md` is the real, loaded contract.
`.agents/rules/AGENTS.md` is intentionally just a 15-line pointer to it
(kept thin on purpose, after a byte-identical copy once drifted) — if
something in `.agents/rules/` seems to contradict `.claude/rules/`,
`.claude/rules/` wins.

## Conventions (see `.claude/rules/AGENTS.md` and `CRAFT_ENGINEERING_GOVERNANCE.md`)

- 100% English in every committed artifact (code, docstrings, comments,
  commit messages, tests). Chat/prose with the owner is pt-BR.
- Zero hardcoded user-facing strings — translation keys in the `translations`
  table (`en-US` source, `pt-BR` default, `es-ES` alternative, always seeded
  together).
- File header used throughout the codebase:
  ```python
  """One-line docstring."""
  # Craft Framework
  # Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
  # Licensed under the MIT License. See LICENSE in the project root.
  ```
- Layer caps: controllers 150 lines/file, 15 lines/action; services 300;
  repositories 250; any function 25 lines / cyclomatic complexity ≤ 6.
- Inside `engine/`, imports are `engine.*`; everywhere else (`app/`,
  `tests/`) imports are `craft.*` (aliased via `sys.modules` in
  `engine/__init__.py`). Do not confuse the two when editing `engine/`
  itself vs. the demo `app/`.
- Never name a third-party framework anywhere (Artisan, Eloquent, Blade,
  Illuminate, Horizon, Nova, Spark, Jetstream, Sail, Valet, or confusable
  variants) — trademark-safety rule, not style.

## Top 10 never-do

1. Never assume `git status` "dirty" means real changes — this repo's
   working tree currently differs from HEAD almost entirely by CRLF vs LF
   line endings (content byte-identical after `tr -d '\r'`). Diff-check
   before reacting to it, and never "clean up" line endings as part of an
   unrelated task.
2. Never edit an already-applied migration; add a new one (forward-only).
3. Never touch `engine/` in a way that isn't covered by the handoff's
   `touches:` list — this core is shared logic, mistakes are amplified.
4. Never hand-roll SQL or markup inside a controller/service — use the
   query builder / Forge templates (structural gate rejects it).
5. Never invent a translation key without writing all three locale rows in
   the same change.
6. Never write a non-English identifier, docstring, comment, or test name.
7. Never claim a test passed without actually running it (container likely
   isn't up — check `docker ps` first).
8. Never touch files outside what the handoff names.
9. Never perform a destructive database operation (drop/truncate/reset) —
   see `.agents/rules/database_safety.md` and `.agents/skills/framework/
  database-safety/SKILL.md`.
10. Never mark a handoff `done` without pasting the actual verification
    command output under `## Result`.

## How to verify your own work

1. `python dev.py route list` if routes changed.
2. Run the specific test file for what you touched; report the real pytest
   output (pass/fail counts), not a guess.
3. Run the two lint gates above from the workspace root if you touched
   anything under `.claude/` scope (i.e., any committed code).
4. If nothing above can run (no container, missing interpreter deps), say so
   explicitly in the handoff's `## Result` — do not report success without
   evidence.

## When to mark a handoff blocked

- The repo state doesn't match what the handoff describes (file missing,
  test already red before your change, migration already applied).
- You cannot start the Docker Compose stack to run tests and the task
  requires runtime verification.
- The task would require editing `engine/` outside the specific function/file
  named in the handoff, or would cross into another project's copy of the
  engine (never edit another project's `data/engine/` from here).
- Any step in "Top 10 never-do" above would be required to complete the task.

Write why under `## Result`, set `status: blocked`, and stop — do not guess
or improvise a workaround for a destructive or out-of-scope step.

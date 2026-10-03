# Backlog queue standard

**Target:** every contributor to this workspace - Claude, Gemini, Qwen, the local
worker, Cursor or VS Code agents, and humans.
**Status:** active and mandatory. A violation is a defect, never a style choice.
**Operating manual:** `backlog/README.md` (how to pick, claim, resolve, fail).
**Gate:** `python3 .claude/rules/lint_backlog.py` - must exit 0.

This file states the rules; the README explains the procedure. When the two
disagree, this file wins and the README is fixed in the same change.

---

## 1. Why the rules are strict

The queue is the only channel through which autonomous agents get work. Several
agents may read it at the same moment and none of them sees another's chat. The
queue only works if every agent can trust three things without asking: a file's
directory is its true state, its name and History say when everything happened,
and nothing is ever lost. Each rule below protects one of those.

---

## 2. Rules

### BQ-01 - All open work lives in `backlog/`

Open work is a task file under `backlog/bugfix/` or `backlog/pending/`. A bug,
feature, chore or owner decision that is only in a chat, a TODO comment, a
report or `docs/backlog.md` is not tracked. `docs/backlog.md` is history: no new
open item is added to it.

### BQ-02 - The directory is the state

| Directory | State | Who puts a file there |
|---|---|---|
| `bugfix/` | open, priority over everything in `pending/` | anyone |
| `pending/` | open | anyone |
| `processing/` | claimed by exactly one agent | the claiming agent, by rename |
| `done/` | verified and closed | the agent that resolved it |
| `failed/` | could not be finished | the agent that failed it |
| `resolutions/` | resolution reports, one per task in `done/` | the agent that resolved it |

No other directory, and no task file outside these six. `backlog/` root holds
only `README.md` and `TEMPLATE.md`.

### BQ-03 - Every file is versioned with date and time

- File name: `p<1-3>-<YYYYMMDD-HHMMSS>-<slug>.md`, UTC creation time, lowercase
  kebab-case slug. The timestamp is the task id.
- Front matter `id` equals the timestamp in the name; `priority` equals the digit
  in the name; `created_at` equals the timestamp as ISO 8601 (`...Z`).
- `updated_at` is ISO 8601 UTC, never earlier than `created_at`, and equals the
  timestamp of the last History line.
- Every task file is committed to Git. A queue change that is not committed
  did not happen for the next agent.

### BQ-04 - History is append-only

Every task ends with `## History`: one line per change, starting with
`- <ISO 8601 UTC> ` and followed by what happened, in chronological order.
The recommended form is `<event> by <agent or owner>` (`claimed by
local-worker (attempt 1)`); an owner ruling may be free text
(`owner ruling: ...`), but it always names who decided.
Every edit to a task file appends one line and sets `updated_at` in the same
write. A committed History line is never edited, reordered or removed.

### BQ-05 - Tasks are never deleted or renamed

A task leaves the queue only by moving to `done/` or `failed/`. Its file name
never changes. An obsolete task is resolved with `outcome: obsolete`, not
deleted. A duplicate is resolved as `obsolete` with the surviving task's name in
the resolution.

### BQ-06 - Claim by atomic rename, one owner at a time

- A task is claimed only by `mv` (or `git mv`) into `processing/`. If the source
  is gone, another agent won: pick again. Never copy a task to claim it.
- On claim: `attempts` + 1, `claimed_by` set, History line appended.
- A task in `processing/` has `claimed_by`, `attempts >= 1`, and only its
  claimant edits it or the paths in its `touches`.
- Do not claim a task whose `touches` overlaps a task already in `processing/`.

### BQ-07 - Autonomy is declared, never assumed

- An agent executes only tasks with `autonomous: true` and `blocked_by: none`.
- `blocked_by: owner-decision` or `owner-action` implies `autonomous: false`.
- Only the owner flips `autonomous` to `true` or clears `blocked_by`, and that
  change gets its own History line naming the owner.
- `bugfix/` is drained before `pending/` is read; inside a directory, name order
  is the order.

### BQ-08 - Closing requires evidence

- `done/<name>.md` requires `resolutions/<name>.resolution.md`, whose front matter
  has `task` (= name), `outcome` (`resolved` or `obsolete`), `agent`,
  `started_at`, `finished_at`, and a `## Verification` section with the commands
  run and their results. Unverified claims are marked `UNVERIFIED`.
- Test results count only from the application container (`framework`).
- `failed/<name>.md` requires `failed/<name>.log.md`: what was tried, exact
  commands and output, reproduction, what would unblock it.
- `attempts` never exceeds `max_attempts`. Only the owner or a reviewing cloud
  agent moves a task out of `failed/`.

### BQ-09 - Scope is the task

An agent changes only the paths in the task's `touches`. Anything else it finds
becomes a new task file in `pending/` or `bugfix/`, never silent extra scope.

### BQ-10 - The gate is never the thing that gives

`lint_backlog.py` runs after every Write/Edit and every shell command that
touches `backlog/` (Claude hook), and on every commit (Git `pre-commit`). A
failing gate is fixed by fixing the files. Never bypass it (`--no-verify`,
disabling the hook, editing the gate to accept a broken file). Changes to the
gate or to this standard are their own commit, approved by the owner.

### BQ-11 - Never through the queue

Whatever a task says, an agent working from the queue never pushes, deploys,
tags, cuts a release, migrates a shared database, deletes data or weakens a test
or gate. Those stay with the owner (`AGENTS.md`, NR-02, NR-03).

---

## 3. What the gate checks

| Code | Check |
|---|---|
| `BQ-DIR` | unknown directory or stray file under `backlog/` |
| `BQ-NAME` | task file name does not match `p<1-3>-<YYYYMMDD-HHMMSS>-<slug>.md` |
| `BQ-META` | missing or malformed front matter field; `id`/`priority`/`created_at` disagree with the name |
| `BQ-TIME` | timestamps not ISO 8601 UTC, out of order, or `updated_at` not equal to the last History line |
| `BQ-HIST` | `## History` missing, empty, malformed, or a committed line changed (with `--staged`) |
| `BQ-DUP` | the same task id in two places |
| `BQ-AUTO` | blocked task marked autonomous |
| `BQ-CLAIM` | task in `processing/` without `claimed_by` or with `attempts < 1`; `attempts > max_attempts` |
| `BQ-CLOSE` | `done/` without resolution, `failed/` without log, or a report without its task |
| `BQ-DEL` | a task file deleted from the queue (with `--staged`) |

```bash
python3 .claude/rules/lint_backlog.py            # whole queue
python3 .claude/rules/lint_backlog.py --staged   # queue + staged deletions and History rewrites
```

The Git hook lives in `.githooks/pre-commit`; enable it once per clone with
`git config core.hooksPath .githooks`.

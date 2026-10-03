# Backlog queue

The work queue for autonomous agents. Every open item is one Markdown file; its
directory is its state. An agent needs nothing but this file and the task file
to pick up, execute and close a task.

```text
backlog/
├── bugfix/        Priority 1 - production incidents, webhooks, broken behavior
├── pending/       Priority 2 - features, roadmap, decisions waiting on the owner
├── processing/    A task an agent is executing right now (one owner)
├── resolutions/   The resolution report an agent writes for each finished task
├── done/          The original task file, archived after a verified resolution
└── failed/        Tasks that could not be completed, with the failure log
```

`docs/backlog.md` keeps the history of items closed before this queue existed
and the `Done automatically` log. Agent-to-agent passing of a task in progress
still goes through `.claude/handoffs/`; the queue says *what* to do, a handoff
says *where someone stopped*.

---

## Task file

Every backlog file is versioned: it lives in Git, its name carries the UTC
date and time it was created, and its body records every change with a UTC
date and time.

File name: `p<priority>-<YYYYMMDD-HHMMSS>-<slug>.md`, for example
`p1-20261003-141200-confirm-postgres-ci.md`.

- `priority` is `1` (highest) to `3`.
- `YYYYMMDD-HHMMSS` is the UTC creation time (`date -u +%Y%m%d-%H%M%S`). It is
  the task id: unique, never reused, no counter to race on.
- Sorting the names sorts the queue: by priority, then oldest first.
- The file name never changes while the task moves between directories;
  resolution and failure files reuse it, so all three line up.

Start from [`TEMPLATE.md`](TEMPLATE.md). Front matter fields:

| Field | Meaning |
|---|---|
| `id` | The `YYYYMMDD-HHMMSS` part of the file name |
| `title` | One line, English |
| `type` | `bugfix`, `feature`, `chore` or `decision` |
| `priority` | `1`-`3`, same as the file name |
| `autonomous` | `true`: an agent may execute it unattended. `false`: skip it |
| `blocked_by` | `none`, `owner-decision` or `owner-action` (what unblocks it) |
| `max_attempts` | Attempts allowed before the task stays in `failed/` (default `2`) |
| `attempts` | Incremented by the agent on every claim |
| `created_at` | UTC creation time, ISO 8601 (`2026-10-03T14:12:00Z`) |
| `updated_at` | UTC time of the last change to the file, ISO 8601 |
| `source` | Where the item came from (audit, backlog section, incident, commit) |
| `touches` | Paths the task may change; editing outside them needs a new task |

Body sections, in order: **Problem**, **Evidence** (with `file:line`),
**Done when** (checkable criteria), **Verify** (exact commands), **Notes**,
**History**.

**History** is append-only, one line per change, newest last:

```text
- 2026-10-03T14:12:00Z created by claude (source: docs/backlog.md L8)
- 2026-10-04T09:30:05Z claimed by local-worker (attempt 1)
- 2026-10-04T09:58:41Z resolved by local-worker (resolutions/p2-20261003-141200-x.resolution.md)
```

Every edit to a task file - claim, scope note, owner decision, move - appends
a History line and sets `updated_at` in the same write.

---

## Lifecycle

```text
bugfix/ or pending/ --claim--> processing/ --verified--> done/  (+ resolutions/<name>.resolution.md)
                                           \--failed---> failed/ (+ failed/<name>.log.md)
```

### 1. Pick

1. `bugfix/` is drained before `pending/` is read.
2. Within a directory, take the first file in name order whose front matter has
   `autonomous: true` and `blocked_by: none`.
3. Skip a task whose `touches` overlaps a task already in `processing/`.

### 2. Claim

Claim by moving the file - a rename is atomic, so only one agent wins:

```bash
mv backlog/pending/p2-20261003-141200-x.md backlog/processing/p2-20261003-141200-x.md
```

If `mv` fails because the source is gone, another agent claimed it: pick again.
After the move, increment `attempts`, set `claimed_by: <agent>` and
`updated_at`, and append a `claimed` History line.

### 3. Execute

- Re-check the **Evidence** first. If the problem no longer exists, resolve the
  task as `obsolete` (step 4) instead of changing code.
- Follow the project rules: `AGENTS.md`, `data/AGENTS.md`, `.claude/rules/`.
- Tests count only when run in the `framework` container (`docker compose up -d`
  if it is down): `docker exec framework sh -lc 'cd /app && python -m pytest tests/<file>.py -q'`.
  `data/.env` sets `APP_URL` to port 9000, so a full-suite run reproduces CI
  only with it moved aside: `mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env`.
  PostgreSQL runs add `-e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable` plus the
  `DB_HOST`/`DB_PORT`/`DB_DATABASE`/`DB_USERNAME`/`DB_PASSWORD` of the local
  database service (values in `data/.env`; never copy them into a task).
- Change only the paths in `touches`. Something else needed? Write a new task
  file in `pending/` and continue, or fail this one with the reason.
- Never: push, deploy, tag, migrate a shared database, delete data, or weaken a
  gate or a test. Those stay with the owner.

### 4. Resolve

When every **Done when** item is verified:

1. Write `resolutions/<task-file-name-without-.md>.resolution.md` from the
   section below.
2. Append a `resolved` History line, set `updated_at`, move the task file to `done/`.
3. Commit the change, the resolution and the move together (Conventional
   Commits, English), unless the owner asked for uncommitted work.

### 5. Fail

When the task cannot be finished - two attempts without a green verification,
a missing credential, an ambiguity no assumption resolves:

1. Write `failed/<task-file-name-without-.md>.log.md`: what was tried, the exact
   command and its output, the reproduction, and what would unblock it.
2. Revert or stash partial changes; list anything left behind in the log.
3. Append a `failed` History line, set `updated_at`, move the task file to `failed/`.

Only the owner or a reviewing cloud agent moves a task out of `failed/`, back to
`pending/` or `bugfix/`, after reading the log. Once `attempts` reaches
`max_attempts`, the task stays in `failed/` until the owner raises the limit.

---

## Resolution file

```markdown
---
task: p2-20261003-141200-x
outcome: resolved | obsolete
agent: <agent and model>
started_at: <UTC ISO 8601>
finished_at: <UTC ISO 8601>
commits: [<sha>, ...]
---

## What changed
Files and behavior, one bullet each.

## Verification
Each command from the task's Verify section, run in the container, with its result.
Anything not verified is marked UNVERIFIED.

## Follow-ups
New task files created, or "none".
```

---

## Writing tasks

- Anyone may add a task: the owner, a reviewer, an agent that finds a defect
  while working. A defect found mid-task becomes a new file, not scope creep.
- A task an agent can execute must be self-contained: no reference to a chat,
  `file:line` evidence, criteria a command can check.
- An owner decision is still a task (`type: decision`, `autonomous: false`,
  `blocked_by: owner-decision`), so it is not lost. When the owner decides,
  they record the decision in the file and either resolve it or flip
  `autonomous` for the implementation.

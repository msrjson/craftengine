# Craft Engine workspace instructions

The running application is `data/`. Read `data/AGENTS.md` before changing its
code. The workspace root holds orchestration files and is not mounted into the
application container. Preserve the existing Git worktree changes.

Do not run destructive database commands or physical deletes in any
environment. Read `.agents/rules/database_safety.md` before database work.

Open work is a queue of task files under `backlog/`. Read `backlog/README.md`
before picking, claiming or closing a task; `bugfix/` is drained before
`pending/`.

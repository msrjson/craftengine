---
id: "20261007-084616"
title: Finish the global `.agents/` migration: two inverted sentences in §0.1, the workspace-guard, and 14 artifacts
type: chore
priority: 2
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-07T08:46:16Z
updated_at: 2026-10-07T08:46:16Z
source: owner ruling 2026-10-07 (global policy: everything is .agents) + audit of ~/.claude/agent-team
touches:
  - ~/.claude/agent-team/AGENTS.md
  - ~/.claude/agent-team/bin/
  - ~/.claude/agent-team/commands/
  - ~/.claude/agent-team/skills/
---

## Problem

The owner ruled that the agent directory is `.agents/` everywhere, with every
tool path a symlink to it, and asked Claude to update the global rules. The
global `AGENTS.md` section 0.1 was rewritten, but the change is incomplete and
two sentences now say the opposite of the rule. This workspace already complies
(`.agents/` physical, `.claude -> .agents`, commit `3e312ca`); the gap is in the
global tooling under `~/.claude/agent-team/`, outside any workspace.

## Evidence

- `~/.claude/agent-team/AGENTS.md:14` — "Tool-specific paths (`.agents/`,
  `.gemini/`, `.qwen/`, ...) never hold content" lists **`.agents/`** as a path
  that must not hold content, when it is the only one that must. Should read
  `` (`.claude/`, `.gemini/`, `.qwen/`, `.cursor/`, ...) ``.
- `~/.claude/agent-team/AGENTS.md:18` — "A project that still has a physical
  `.agents/` (or another vendor directory) is migrated" should read "a physical
  `.claude/`"; as written it orders the migration of the directory the rule
  requires.
- `~/.claude/agent-team/bin/workspace-guard` — still says "It may be `.claude/`
  or the vendor-neutral `.agents/`, whichever the owner chose" and
  `TOOL_DIRS = {".gemini", ".qwen", ".cursor"}`. Under the new rule it must
  refuse a physical `.claude/` (accepting the symlink), i.e. treat `.claude` as
  a tool path that must be a symlink. Today it silently allows a physical
  `.claude/`, so the rule is not enforced.
- Still using `.claude/` paths (functional only through the symlink):
  `bin/affected-tests` (2), `bin/do-app` (6), `bin/handoff` (6), `bin/journey`
  (3), `bin/local-worker` (12), `bin/shift-signal` (3), `bin/team` (2),
  `bin/team-setup` (8), `bin/ws-creds` (6), `commands/retomar.toml` (1),
  `commands/turno.md` (1), `commands/turno.toml` (1),
  `skills/agent-handoff/SKILL.md` (2).

## Done when

- [ ] The two inverted sentences in §0.1 say `.claude/` where they must.
- [ ] `workspace-guard` denies a physical `.claude/` and points at `.agents`,
      keeping the "write only inside your own workspace" rule untouched, with a
      backup of the previous file.
- [ ] The listed artifacts name `.agents/...` (the symlink keeps them working
      either way, so this is consistency, not a break).
- [ ] A global grep for `\.claude/` in `~/.claude/agent-team/{bin,commands,skills,templates}`
      finds only legitimate references to the home directory.

## Verify

```bash
grep -n 'Tool-specific paths\|still has a physical' ~/.claude/agent-team/AGENTS.md
grep -n 'TOOL_DIRS' ~/.claude/agent-team/bin/workspace-guard
grep -rn '\.claude/' ~/.claude/agent-team/bin ~/.claude/agent-team/commands ~/.claude/agent-team/skills | grep -v 'agent-team' | head
```

## Notes

Outside every workspace: no agent session may edit `~/.claude/agent-team/`
(global rule 2, write only inside your own workspace) without the owner's
explicit go-ahead; this task records the gap so it is not lost while Claude
finishes the rewrite. The owner's ruling of 2026-10-07 is the authority. The
`workspace-guard` must keep denying writes into another workspace; only the
`.claude`-as-symlink check is added.

## History

- 2026-10-07T08:46:16Z created by qwen@qwen-code (source: owner ruling 2026-10-07; audit of the global artifacts)

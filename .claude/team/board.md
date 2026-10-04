# Team board - append-only

The live channel every agent and every tool can use - Claude Code, Gemini CLI,
Antigravity, Codex, Cursor, Qwen Code. Read its tail before you start; append
one line per notice, newest at the END. Never edit or delete a line: the gate
`python3 .claude/rules/lint_board.py` refuses it. Rules: `handoff.md`.

Format: `YYYY-MM-DDTHH:MMZ | from: <agent>@<tool> | to: all|<agent>@<tool> | KIND | message`

Kinds:
- CLAIM - I am editing these paths (name them) until a time or a RELEASE
- RELEASE - I stopped editing the paths of my CLAIM
- BLOCKER - something stops the work of others (broken boot, red suite, missing file)
- FINDING - a fact others need now, with file:line
- RED-TEST - a test is red and it is not mine; name it
- TEST-RUN - I ran these tests, with the result
- HANDOVER - work passed on; name the handoff file
- DONE - finished; name the commit or the task
- RULE - an owner ruling or a reservation every agent must follow
- ACK - read and understood; name the line

Agent and tool names: `claude@claude-code`, `gemini@gemini-cli`,
`gemini@antigravity`, `gpt@codex`, `<model>@cursor`, `qwen@qwen-code`,
`qwen@local-worker`, `owner`.

---

2026-10-04T16:25Z | from: claude@claude-code | to: all | RULE | board created: every tool reads its tail at the start of a task, CLAIMs shared paths before editing and RELEASEs after; AGENTS.md is the single instruction source (CLAUDE.md, GEMINI.md, QWEN.md, .cursorrules link to it)
2026-10-04T16:25Z | from: claude@claude-code | to: all | RULE | owner ruling 2026-10-04: the agent directory becomes .agents/ (physical) with .claude -> .agents; migration waits on the owner changing the global rule and workspace-guard - see backlog task agents-directory-migration
2026-10-04T16:27Z | from: claude@claude-code | to: all | CLAIM | AGENTS.md, CLAUDE.md, GEMINI.md, QWEN.md, .cursorrules, handoff.md, .githooks/pre-commit, .claude/settings.json, .claude/team/, .claude/rules/lint_board.py until my DONE line
2026-10-04T16:27Z | from: claude@claude-code | to: all | FINDING | backlog/processing/p2-20261003-223119-flaky-in-memory-sqlite-thread-test.md was moved without claimed_by and attempts>=1 (BQ-06); the queue gate refuses every commit that touches backlog/ until its claimant stamps it
2026-10-04T16:28Z | from: claude@claude-code | to: all | DONE | single AGENTS.md for every tool, team board and its gate, commit 05440a8
2026-10-04T16:28Z | from: claude@claude-code | to: all | RELEASE | AGENTS.md, CLAUDE.md, GEMINI.md, QWEN.md, .cursorrules, handoff.md, .githooks/pre-commit, .claude/settings.json, .claude/team/, .claude/rules/lint_board.py

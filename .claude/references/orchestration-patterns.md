# Orchestration Patterns

The catalog of agent orchestration patterns the Craft Engine agent catalog endorses, and
the anti-patterns to avoid. Read it before adding a slash command that coordinates
several agents, or before introducing an agent that "wraps" existing ones.

**The governing rule: the user, or a slash command, is the orchestrator. Agents
(personas) never invoke other agents. Skills are mandatory hops inside an agent's
workflow.**

---

## The three layers

| Layer | What it is | Example | Composition role |
|---|---|---|---|
| **Skill** | A workflow with steps and exit criteria | `code-review-and-quality` | The *how*: loaded from inside an agent or a command |
| **Agent** | A persona with one perspective and one report format | `code-reviewer` | The *who*: adopts a viewpoint, produces a report |
| **Command** | A user-facing entry point | `/review-change`, `/ship` | The *when*: composes agents and skills |

Installed layout in a project (`python dev.py agent:install <name>...`):

```
.claude/
  agents/code-reviewer.md
  agents/security-auditor.md
  agents/test-engineer.md
  agents/web-performance-auditor.md
  skills/<skill-name>/SKILL.md
  commands/<command-name>.md
  references/<reference-name>.md
```

### Rules for agents

1. An agent is one role with one output format. If a second role creeps in, create a
   second agent.
2. **Agents never invoke other agents.** Composition belongs to commands or to the user.
   The harness enforces this too: a subagent cannot spawn another subagent.
3. An agent may load skills (the *how*) and read references.
4. Every agent file ends with a `## Composition` block stating when to invoke it
   directly, which commands invoke it, and that it is not invoked from another agent.
5. An agent that recommends a second perspective says so in its report ("recommend a
   `security-auditor` pass on `app/Http/Controllers/Auth/`"); it does not run that pass
   itself.

---

## Endorsed patterns

### 1. Direct invocation (no orchestration)

One agent, one perspective, one artifact. The default and the cheapest option.

```
user -> code-reviewer -> report -> user
```

**Use when:** the work is one perspective on one artifact and fits in one sentence.

**Examples:**

- "Review this pull request" -> `code-reviewer`
- "Find security issues in `app/Http/Controllers/Auth/LoginController.py`" ->
  `security-auditor`
- "Which tests are missing for the checkout flow?" -> `test-engineer`
- "Audit Core Web Vitals on the product page" -> `web-performance-auditor`

**Cost:** one round trip. This is the baseline every orchestrated pattern must beat.

---

### 2. Single-agent slash command

A command that wraps one agent together with the project's skills, so the user does not
re-explain the workflow every time.

```
/review-change -> code-reviewer (with the code-review-and-quality skill) -> report
```

**Use when:** the same single-agent invocation repeats with the same setup.

**Examples in the catalog:** `/review-change` (`code-reviewer`), `/test`
(`test-engineer` with `test-driven-development`), `/webperf`
(`web-performance-auditor`), `/code-simplify` (the `code-simplification` skill).

**Cost:** the same as direct invocation. The command is a saved prompt.

**Anti-signal:** if the command body is mostly "decide which agent to call", delete it
and let the user call the agent directly.

---

### 3. Parallel fan-out with merge

Several agents work on the same input at the same time, each producing an independent
report. A merge step, in the main session's context, synthesizes them into one decision.

```
                        +-> code-reviewer    -+
/ship -> fan out  ------+-> security-auditor -+-> merge -> go/no-go + rollback plan
                        +-> test-engineer    -+
```

`/ship` is the canonical example in the catalog:

- Each agent reads the same diff but produces a **different kind** of finding: code
  quality and layer caps, vulnerabilities and privacy exposure, test coverage and
  failing gates.
- They share no mutable state and have no ordering dependency, so parallelism is real
  and wall-clock time drops.
- Each runs in its own fresh context, so the main session stays uncluttered.
- The merge is small and benefits from full context, so it stays in the main session,
  where the release checks are applied: `python -m pytest tests`, `ruff check engine`,
  `python .claude/rules/lint_language.py`, `python .claude/rules/lint_structure.py`, a
  `CHANGELOG.md` entry under `## [Unreleased]`, forward-only migrations, and a rollback
  plan.

**Use when:**

- The sub-tasks are genuinely independent (no shared mutable state, no ordering)
- Each sub-agent benefits from its own context window
- The merge step fits in the main session's remaining context
- Wall-clock latency matters

**Cost:** N parallel sub-agent contexts plus one merge turn. More than direct invocation,
but faster in wall-clock time and with better reports, because each sub-agent stays
focused on one perspective.

**Validation checklist before adopting this pattern:**

- [ ] Can every sub-agent run at the same time without ordering issues?
- [ ] Does each agent produce a different *kind* of finding, not the same finding from
      another angle?
- [ ] Will the merge fit in the main session's remaining context?
- [ ] Is the user's wait long enough that parallelism is noticeable?

If any answer is no, fall back to direct invocation or a single-agent command.

**Mechanics:** a fan-out only runs in parallel when all sub-agent invocations are issued
**in the same assistant turn**. Invocations in consecutive turns run one after another.
`/ship` states this explicitly, and any new orchestrating command must do the same.

---

### 4. Sequential pipeline as user-driven slash commands

The user runs commands in a defined order, carrying context (or commit history) between
them. There is no orchestrator agent: the user *is* the orchestrator.

```
user runs:  /spec  ->  /plan-tasks  ->  /build  ->  /test  ->  /review-change  ->  /ship
```

**Use when:** each step needs the previous step's output, and human judgment between
steps adds value.

**Example in the catalog:** the whole define -> plan -> build -> verify -> review -> ship
lifecycle, optionally preceded by the `interview-me` and `idea-refine` skills and by
`/constraints`.

**Cost:** one context per step. The orchestration layer is free, because there is no
orchestrator agent.

**Why not automate it:** an LLM "lifecycle orchestrator" would (a) lose nuance between
steps, because it must summarize for each hand-off, (b) skip the human checkpoints that
catch wrong-direction work early, and (c) roughly double the token cost with paraphrasing
turns.

---

### 5. Research isolation (context preservation)

When a task needs a large amount of reading that should not pollute the main context,
spawn a research sub-agent that returns only a digest.

```
main session -> research sub-agent (reads 50 files) -> digest -> main session continues
```

**Use when:**

- The main session must stay focused on a downstream task
- The result is much smaller than the material it consumes
- Decision quality benefits from leaving the main session room to think

**Examples:** "Find every call site of this deprecated facade method across the
application", "Summarize what these 30 ADRs say about caching", "List every Forge
template that renders a state-changing form without `@csrf`".

**Cost:** one isolated context. Worth it whenever the alternative is loading hundreds of
files into the main session.

**Prefer the harness's built-in read-only exploration subagent** over defining a custom
research agent. Define a custom one only when the built-in does not fit, for example
when a domain-specific system prompt is needed that the model would not infer.

---

## Subagents versus agent teams

The `.claude/` harness offers two parallelism primitives. Pattern 3 maps to
**subagents**. When workers must talk to each other, use **agent teams** instead.

| | Subagents | Agent teams |
|---|---|---|
| Coordination | The main session fans out; sub-agents only report back | Teammates message each other and share a task list |
| Context | One context window per subagent | One context window per teammate |
| When to use | Independent tasks that produce reports | Collaborative work that needs discussion |
| Availability | Stable | Experimental; must be enabled in the harness settings |
| Cost | Lower | Higher: every teammate is a separate model instance |

**The catalog agents work in both modes.** Spawned as subagents (for example by
`/ship`), they report findings to the main session. Spawned as teammates, they can
challenge each other's findings directly. The agent definition is the same; only the
spawning context changes.

One subtlety: frontmatter fields that preload skills or tool servers for an agent are
honored when it runs as a subagent, but a teammate loads skills from the project and
user settings like a regular session. If an agent depends on a specific skill being
available, make sure it is installed under `.claude/skills/` so it is present in both
modes.

### Rules the harness enforces

Two catalog rules are not only convention:

- **Subagents cannot spawn other subagents.** Anti-pattern B (agent calls agent) and
  anti-pattern D (deep agent trees) cannot exist by construction.
- **No nested teams.** Teammates cannot start their own teams; the same anti-patterns are
  blocked at the team level.

The patterns in this catalog can be adopted without worrying that contributors will
accidentally build the anti-patterns: those simply fail to run.

### Built-in subagents

Before defining a custom agent, check whether a built-in one already covers the role:

| Built-in role | Purpose |
|---|---|
| Read-only exploration | Codebase search and analysis. Use it for pattern 5 (research isolation). |
| Planning | Read-only research while designing an implementation plan. |
| General purpose | Multi-step tasks that need both exploration and modification. |

Do not redefine these. Layer the specialist agents (`code-reviewer`,
`security-auditor`, `test-engineer`, `web-performance-auditor`) on top of them.

### Agent frontmatter

Catalog agents use `name`, `description` (one line saying when to invoke) and `tools`.
Reviewers and auditors are read-only (`Read, Grep, Glob`), adding `Bash` only when they
must run the test suite or the gates. A per-agent `model` field can tune cost (a lighter
model for coverage scans, a stronger one for security audits); add it in the project's
installed copy under `.claude/agents/` rather than in the catalog, since it is a local
cost decision.

---

## Worked example: agent teams for competing-hypothesis debugging

This example shows when to reach for **agent teams** instead of `/ship`'s subagent
fan-out. From a distance they look alike (both spawn the same three agents), but the
value comes from a different place.

### The scenario

> *Checkout occasionally hangs for about 30 seconds before completing, roughly once every
> 50 sessions. No errors in the logs. It started after last week's release.*

Plausible root causes, mutually exclusive, all consistent with the symptoms:

1. A race in the new payment-confirmation flow: an async action awaiting a call that
   blocks the event loop, or a pooled database connection not released in a worker
   thread
2. An authorization check (a Gate policy) that occasionally falls through to a slow
   synchronous network call
3. A missing index on a query whose cost grows with cart size
4. A flaky payment gateway plugin whose client retries silently before timing out

A single agent picks the first plausible theory and stops. A `/ship`-style fan-out would
have each agent report independently, but the reports never meet, so nothing rules the
wrong theories out.

This is the case agent teams exist for: with several independent investigators actively
trying to disprove each other, the theory that survives is far more likely to be the
real root cause.

### Why this is not a `/ship` job

| | `/ship` (subagents) | Agent teams |
|---|---|---|
| Sub-agents see | The same diff through different lenses | A shared task list and each other's messages |
| Output | Three independent reports, one merge | Adversarial debate, consensus root cause |
| Right when | You want a verdict on a known artifact | You want to *find* the artifact among hypotheses |

`/ship` is a verdict; an agent team is an investigation.

### Setup

Agent teams are experimental and must be enabled in the harness settings once per
environment. The catalog agents installed under `.claude/agents/` are picked up
automatically; there are no team configuration files to write.

### The trigger prompt

Typed into the lead session in natural language:

```
Users report checkout hangs for about 30 seconds intermittently since last
week's release. No errors in the logs.

Create an agent team to debug this with competing hypotheses. Spawn three
teammates using the existing agent types:

  - code-reviewer    - investigate races and blocking calls in the checkout
                       path: async actions, worker threads, connection pool release
  - security-auditor - investigate Gate policies, session handling and any
                       synchronous network call added to authorization recently
  - test-engineer    - propose pytest tests that distinguish between the
                       hypotheses and check coverage gaps in checkout

Have them message each other directly to challenge each other's theories.
Update the findings as consensus emerges. Converge only when two teammates
agree they can disprove the others.
```

The lead spawns three teammates that reference the existing agent names. Each agent's
body is **appended** to its teammate's system prompt as additional instructions, on top
of the coordination instructions the lead installs; the trigger prompt becomes their
task.

### What happens

1. Each teammate runs in its own context window and explores the codebase through its
   own lens.
2. Teammates send findings to each other directly; the lead does not have to relay.
3. The shared task list shows who is investigating what at any moment.
4. When `code-reviewer` finds an async action that awaits a synchronous gateway call on
   the event loop, it messages `security-auditor` to confirm the authorization check is
   not part of the same path. `security-auditor` checks and replies, either confirming
   the race is the real issue or producing counter-evidence.
5. `test-engineer` proposes a focused integration test for the leading theory, and the
   team uses it to verify before declaring consensus.
6. The lead synthesizes the converged finding and presents it to the user.

The user can interrupt any teammate directly to redirect an investigator who has gone
down the wrong path.

### When to clean up

When the investigation lands on a root cause, tell the lead:

```
Clean up the team
```

Always clean up through the lead, never through a teammate: teammates lack the full team
context needed for cleanup.

### Cost expectation

Three teammates investigating for ten to fifteen minutes cost noticeably more than the
same three agents spawned as subagents by `/ship`. The justification is the *quality of
the conclusion*: in production debugging, where the wrong fix is expensive, the extra
tokens are a bargain. For a routine pull request review, stay with `/review-change` or
`/ship`.

### The anti-pattern in this scenario

Do **not** rebuild this as a `/debug` slash command that fans out subagents. Subagents
cannot message each other, so the adversarial debate that makes the pattern work would
be lost. If the workflow keeps recurring, keep the trigger prompt above as a documented
snippet instead of wrapping it in a command that misuses subagents. For a single
investigator, the `debugging-and-error-recovery` skill
(`.claude/skills/debugging-and-error-recovery/SKILL.md`) is the right tool.

### When not to use agent teams

- A production-bound verdict on a known diff -> `/ship` (subagents)
- One specialist perspective on one artifact -> direct agent invocation
- A sequential lifecycle (spec -> plan -> build) -> user-driven commands (pattern 4)
- Read-heavy research with a small digest -> the built-in exploration subagent

Reach for agent teams only when teammates **need** to challenge each other to reach the
right answer.

---

## Anti-patterns

### A. Router agent ("meta-orchestrator")

An agent whose job is to decide which other agent to call.

```
/work -> router-agent -> "this needs a review" -> code-reviewer -> router (paraphrases) -> user
```

**Why it fails:**

- A pure routing layer with no domain value
- Two paraphrasing hops: information loss and roughly twice the token cost
- The user already knew they wanted a review and could have run `/review-change`
- It duplicates what slash commands and the intent map already do

**What to do instead:** add or refine slash commands, and keep the intent -> entry map in
the `using-agent-catalog` skill (`.claude/skills/using-agent-catalog/SKILL.md`). That
skill routes by telling the main session which entry to load; it is not an agent and
never delegates.

---

### B. Agent that calls another agent

A `code-reviewer` that internally invokes `security-auditor` when it sees
authentication code.

**Why it fails:**

- Agents are designed to produce one perspective; chaining them defeats that
- The summary the caller passes loses context the callee needs
- Failure modes multiply: whose output format wins, whose rules apply?
- It hides cost from the user

**What to do instead:** the calling agent *recommends* a follow-up audit in its report.
The user or a command runs the second pass.

---

### C. Sequential orchestrator that paraphrases

An agent that runs `/spec`, then `/plan-tasks`, then `/build`, and so on, on the user's
behalf.

**Why it fails:**

- It removes the human checkpoints that catch wrong-direction work
- Every hand-off summarizes context, so drift accumulates over a long pipeline
- It doubles token cost: an orchestrator turn plus a sub-agent turn for every step
- It removes user agency exactly where judgment matters most

**What to do instead:** keep the user as the orchestrator. Document the recommended
sequence (the lifecycle in the `using-agent-catalog` skill) and let the user run it.

---

### D. Deep agent trees

`/ship` calls a `pre-ship-coordinator`, which calls a `quality-coordinator`, which calls
`code-reviewer`.

**Why it fails:**

- Every layer adds latency and tokens with no decision value
- Debugging becomes a multi-level investigation
- The leaf agents lose context to several summarization steps

**What to do instead:** keep orchestration depth at one at most (command -> agents). The
merge happens in the main session.

---

## Decision flow

When considering a new orchestrated workflow, walk this flow:

```
Is the work one perspective on one artifact?
|-- Yes -> Direct invocation. Stop.
`-- No  -> Will the same composition repeat?
          |-- No  -> Direct invocation, ad hoc. Stop.
          `-- Yes -> Are the sub-tasks independent?
                    |-- No  -> Sequential commands run by the user (pattern 4).
                    `-- Yes -> Do the workers need to challenge each other?
                              |-- Yes -> Agent team, documented as a trigger prompt.
                              `-- No  -> Parallel fan-out with merge (pattern 3).
                                         Validate against the checklist above.
                                         If any check fails -> single-agent command (pattern 2).
```

---

## When to add a new pattern to this catalog

Add an entry only after:

1. The pattern has been used at least twice in real work
2. A concrete artifact in the catalog demonstrates it
3. You can explain why an existing pattern would not have worked
4. You can describe its anti-pattern shadow: what people will mistakenly build instead

When a new agent enables a new orchestration pattern, document the pattern here rather
than inventing it inside the agent file. Premature entries become aspirational
documentation that nobody follows.

# AI Agent Integration & Discovery Guide

Start with [Authentication](authentication.md) before creating login links or
changing route protection. The starter uses `/login`; `GET /signin` redirects
there. Inspect the live route table with `python dev.py route list --json`.

Craft Engine is designed from the ground up to be **AI-Native** and exceptionally developer-friendly for both humans and autonomous coding agents (Cursor, Claude Code, GitHub Copilot, Windsurf, AGY).

---

## 🤖 Why Craft Engine is Agent-Friendly

1. **Small, conventional surface**:
   The primitives are few and predictable, but they are Craft's own - verify
   them in `engine/` rather than assuming another framework's API:
   - `Model.find(id)` / `Model.query().where(...)`
   - `Route.get(...)` / `Route.post(...)`
   - `Validator(data, rules)` - a constructor; there is no `Validator.make`
   - A `FormRequest` subclass validates, and with `antispam = True` also runs
     the honeypot and time trap: `LoginRequest(request).passes()`
   - Controllers, FormRequests, Resources, and Forge templates.
2. **Deterministic CLI Tooling**:
   - Every file can be generated deterministically via `python dev.py make:*` (`make:model`, `make:controller`, `make:request`, `make:crud`, `make:auth`).
   - Predictable directory structures: `app/Models`, `app/Http/Controllers`, `database/migrations`, `resources/views`.
3. **Absolute Data Persistence**:
   - Clear architectural constraints prevent catastrophic data wipes. Destructive commands (`migrate:fresh`, `db:wipe`) are hard-blocked.
4. **Standardized Context Files (`llms.txt`)**:
   - Adheres to the [llmstxt.org](https://llmstxt.org/) specification for zero-friction LLM indexing.

---

## ⚡ AI Ready Out-of-the-Box (Skills, Rules & Agents)

Craft Engine is born **100% pre-configured** with all skills, rules, and agents necessary for a developer and autonomous AI agents:
- `.agents/rules/AGENTS.md` — Strict AI contributor contract (forward-only migrations, absolute data persistence, English codebase, zero hardcoded strings, zero guessing).
- `.agents/skills/` — 27 complete development skills (spec-driven, TDD, security hardening, performance, incremental implementation).
- `.agents/agents/` — 4 specialized agent roles from the catalog (`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`), plus the `team-lead` coordination agent.
- `.agents/commands/` — 9 workflow commands (`/spec`, `/plan-tasks`, `/build`, `/test`, `/ship`, `/review-change`, `/code-simplify`, `/constraints`, `/webperf`).
- `.cursorrules` & `llms.txt` / `llms-full.txt` — Zero-friction context indexing.

`.agents/` is the single physical agent directory; `.claude` is a symlink to it,
so a harness that insists on its own path still finds the files. Both
`agent:scaffold` and `agent:install` create that link. A project that still
carries a physical `.claude/` directory is refused with `AGENT_LEGACY_DIRECTORY`
before anything is written: move its contents into `.agents/`, replace `.claude`
with a symlink to `.agents`, and run the command again. On a filesystem without
symlink support the catalog still lands in `.agents/` and only the link is
skipped.

If you ever need to re-scaffold or re-sync agent rules and context, run:

```bash
python dev.py agent:scaffold
```

This generates or refreshes:
- `.cursorrules` — Directives for Cursor and IDE assistants, setting guidelines for file paths, facades, validation rules, and database safety.
- `llms.txt` — Standard high-density overview of Craft Engine for LLMs.
- `llms-full.txt` — Full API contracts and code examples.
- `AGENTS.md` — Short, tool-neutral entry point at the project root.
- `.agents/rules/AGENTS.md` — Canonical AI governance contract.
- `.agents/agents/`, `.agents/skills/`, `.agents/commands/`, `.agents/references/` — The full development agent catalog.

It also generates the files several agents and sessions need to work on one
project without sharing memory, and the verification a fresh project starts
with:

| File | Purpose |
|---|---|
| `.agents/team/board.md` | Append-only team board: claims, releases, blockers, findings |
| `.agents/lessons.md` | One line per mistake worth not repeating |
| `.agents/handoffs/` | Where one agent leaves work for the next |
| `.agents/multi-session-coordination.md` | The coordination rules in short |
| `.agents/journeys/smoke.json` | A smoke journey: `GET /health` expects `200` |
| `.agents/validation.json` | The container, the suite command and the journeys to run |
| `.agents/agents/team-lead.md` | The `team-lead` agent, which coordinates through the board and handoffs |
| `.agents/hooks/environment_guard.sh` | Exits 1 outside a container, so the suite only counts where the real database is |
| `.githooks/pre-commit` | Runs the guard and the suite; enable once with `git config core.hooksPath .githooks` |
| `.github/workflows/ci.yml` | Installs the project with the `dev` extra and runs the suite on push and pull request |
| `.vscode/tasks.json`, `.vscode/launch.json` | A default `test` task and a launch entry for the current test file |

Without `--force` the command stops at the first of `.cursorrules`, `llms.txt`,
`llms-full.txt` or a catalog entry that already exists. The coordination and
verification files above, and both `AGENTS.md` files, are kept when present and
rewritten only with `--force` - which then also resets the board and the
lessons file to their initial content, so keep them under version control.

> The smoke journey calls `/health`, which answers only when
> `HEALTH_ROUTES_ENABLED=true`. `validation.json` names the container `app`;
> edit it to match the project's own container name.

---

## Development Agent Catalog

The framework ships an installable catalog of development specialists, adapted to
Craft Engine (`dev.py`, Craft ORM, Forge, pytest, forward-only migrations,
database-backed i18n, the layer caps and both lint gates). It lives in
`engine/cli/agent_catalog/` and is installed per project:

```bash
python dev.py agent:list                     # everything, with descriptions
python dev.py agent:install --all            # the whole catalog
python dev.py agent:install security-auditor security-and-hardening
```

Three layers, each with one job:

| Layer | What it is | Installed to |
|---|---|---|
| **Agent** | A role with one perspective and one report format | `.agents/agents/<name>.md` |
| **Skill** | A workflow with steps and exit criteria | `.agents/skills/<name>/SKILL.md` |
| **Command** | A user entry point that composes agents and skills | `.agents/commands/<name>.md` |

Shared checklists (`.agents/references/`) are installed with any selection, because
agents and skills link to them. Agents never call other agents; commands orchestrate.

### Agents

| Agent | Use for |
|---|---|
| `code-reviewer` | Five-axis review of a change before merge, including Craft governance |
| `security-auditor` | Vulnerability and hardening audit |
| `test-engineer` | Test strategy, coverage gaps, prove-it tests for bugs |
| `web-performance-auditor` | Core Web Vitals, loading, rendering and network analysis |

### Commands

| Command | Flow |
|---|---|
| `/spec` | Write the specification before code |
| `/plan-tasks` | Break a spec into ordered, verifiable tasks |
| `/build` | Implement the next task in thin, tested slices |
| `/test` | Test-driven workflow for a feature or a bug |
| `/review-change` | Single-perspective review with `code-reviewer` |
| `/code-simplify` | Reduce complexity without changing behavior |
| `/constraints` | Derive and enforce the constraints of a change |
| `/ship` | Parallel review, security and coverage reports, then go/no-go |
| `/webperf` | Web performance audit |

### Skills

`api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`,
`code-review-and-quality`, `code-simplification`, `constraint-driven-development`,
`context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`,
`documentation-and-adrs`, `doubt-driven-development`, `frontend-ui-engineering`,
`git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`,
`interview-me`, `observability-and-instrumentation`, `performance-optimization`,
`planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`,
`source-driven-development`, `spec-driven-development`, `test-driven-development`,
`using-agent-catalog` (start here: it routes an intent to the right skill, agent or command).

Two skills are specific to Craft Engine:

| Skill | What it enforces |
|---|---|
| `tests-in-container` | A test result counts as evidence only when it comes from the application container |
| `craft-engine-pitfalls` | The recurring traps: assuming parity with another framework, forward-only data, relations as methods, the engine boundary, and `.agents/` |

---

## 🛡️ Form Validation & Anti-Spam in Agent Code

When AI agents generate forms, Craft Engine provides single-line directives for complete bot defense and validation feedback:

```html
<!-- resources/views/contact.forge.py -->
@extends("layouts.app")

@section("content")
<form action="/contact" method="POST">
    @csrf
    @honeypot

    <div>
        <label>Your Email</label>
        <input type="email" name="email" value="{{ old('email', '') }}">
        @error('email')
            <span class="error">{{ message }}</span>
        @enderror
    </div>

    <button type="submit">Send</button>
</form>
@endsection
```

And in the controller:

```python
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.validation.validator import Validator


class ContactController(Controller):
    def store(self, request):
        validator = Validator.make(
            request.all(),
            {
                "email": ["required", "email"],
                "message": ["required", "text", "no_html", "spam_free"],
            },
        )

        if validator.fails():
            return redirect.back().with_errors(validator.errors()).with_input()

        # Process contact message...
        return redirect(route="contact.success")
```

---

## 🛠️ Scaffolding Authentication (`make:auth`)

To generate a complete, working authentication system:

```bash
python dev.py make:auth
```

This scaffolds:
- `app/Http/Controllers/Auth/AuthController.py`
- `app/Http/Requests/Auth/LoginRequest.py`
- `app/Http/Requests/Auth/RegisterRequest.py`
- `resources/views/auth/login.forge.py` (with `@csrf`, `@honeypot`, `@error`)
- `resources/views/auth/register.forge.py`
- `resources/views/auth/dashboard.forge.py`
- In a new application, wires `/login`, the `GET /signin` redirect, `/register`,
  `/logout`, and a protected `/dashboard` into `routes/web.py`.

If the application already has a login route and controller, `make:auth`
preserves them, including when `--force` is supplied. This avoids replacing
an existing CAPTCHA or redirect flow with generated code.

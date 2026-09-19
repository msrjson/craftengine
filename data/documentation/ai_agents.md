# AI Agent Integration & Discovery Guide

Craft Engine is designed from the ground up to be **AI-Native** and exceptionally developer-friendly for both humans and autonomous coding agents (Cursor, Claude Code, GitHub Copilot, Windsurf, AGY).

---

## 🤖 Why Craft Engine is Agent-Friendly

1. **Active Record & Laravel-Style Ergonomics**:
   LLMs have been trained on vast amounts of Laravel, Django, and FastAPI code. Craft Engine uses the exact same intuitive mental models:
   - `Model.find(id)` / `Model.where(...)`
   - `Route.get(...)` / `Route.post(...)`
   - `Validator.make(data, rules)`
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
- `.claude/rules/AGENTS.md` & `.agents/rules/AGENTS.md` — Strict AI contributor contract (forward-only migrations, absolute data persistence, English codebase, zero hardcoded strings, zero guessing).
- `.claude/skills/` — 25 complete development skills (spec-driven, TDD, security hardening, performance, incremental implementation).
- `.claude/agents/` — 4 specialized agent roles (`code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`).
- `.claude/commands/` — 8 workflow commands (`/spec`, `/build`, `/test`, `/ship`, `/review-change`, `/code-simplify`, `/constraints`, `/webperf`).
- `.cursorrules` & `llms.txt` / `llms-full.txt` — Zero-friction context indexing.

If you ever need to re-scaffold or re-sync agent rules and context, run:

```bash
python dev.py agent:scaffold
```

This generates or refreshes:
- `.cursorrules` — Directives for Cursor and IDE assistants, setting guidelines for file paths, facades, validation rules, and database safety.
- `llms.txt` — Standard high-density overview of Craft Engine for LLMs.
- `llms-full.txt` — Full API contracts and code examples.
- `.claude/rules/AGENTS.md` & `.agents/rules/AGENTS.md` — Canonical AI governance contract.
- `.agents/mcp.json` — Model Context Protocol config snippet.
- `.claude/agents/`, `.claude/skills/`, `.claude/commands/`, `.claude/references/` — The full development agent catalog.

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
| **Agent** | A role with one perspective and one report format | `.claude/agents/<name>.md` |
| **Skill** | A workflow with steps and exit criteria | `.claude/skills/<name>/SKILL.md` |
| **Command** | A user entry point that composes agents and skills | `.claude/commands/<name>.md` |

Shared checklists (`.claude/references/`) are installed with any selection, because
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
        validator = Validator.make(request.all(), {
            "email": ["required", "email"],
            "message": ["required", "text", "no_html", "spam_free"],
        })

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
- Idempotently wires `/login`, `/register`, `/logout`, and `/dashboard` into `routes/web.py`.

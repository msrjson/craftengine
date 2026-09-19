"""
AgentScaffolder: AI agent discovery and integration scaffolding for Craft Engine.

Category: Core Framework (CLI).
Relations:
  - Invoked from `dev.py agent:scaffold` (`engine/cli/app.py`).
  - Generates `.cursorrules`, `.claude/rules/AGENTS.md`, `.agents/rules/AGENTS.md`,
    `llms.txt`, `llms-full.txt`, and `.agents/mcp.json`.
  - Installs the development agent catalog (`engine/cli/agent_catalog/`) into `.claude/`.
References:
  - Guide: `documentation/ai_agents.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
from typing import Any, Dict

from engine.cli import agent_catalog


def _write_file(path: str, content: str, force: bool = False) -> str:
    if os.path.exists(path) and not force:
        raise FileExistsError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def cursorrules_content() -> str:
    return """# Craft Engine — AI Assistant Rules (.cursorrules)

You are an expert full-stack developer working on a Craft Engine project.
Craft Engine is an async-first Python web framework inspired by Laravel, featuring Active Record ORM, Typer CLI, Forge template engine, and Facades.

## 1. CORE ARCHITECTURAL INVARIANTS
- Framework: Craft Engine (Python 3.11+, async-first).
- CLI Entrypoint: `python dev.py <command>` (never use artisan or django-admin).
- Absolute Data Persistence: NEVER execute destructive database commands (`migrate:fresh`, `migrate:reset`, `db:wipe`, `db:drop`). Schema evolution is strictly forward-only (`python dev.py migrate`).
- Language: 100% English code, identifiers, docstrings, and commits. Responses to the user should follow the user's language (e.g. Portuguese pt-BR if requested).

## 2. DIRECTORY STRUCTURE
- `app/Models/` — Active Record ORM models inheriting from `craft.orm.model.Model`.
- `app/Http/Controllers/` — HTTP Controllers inheriting from `craft.http.controller.Controller`.
- `app/Http/Requests/` — Form requests inheriting from `craft.validation.form_request.FormRequest`.
- `app/Http/Resources/` — JSON API transformers inheriting from `craft.resources.Resource`.
- `database/migrations/` — Forward-only schema migrations.
- `resources/views/` — Forge templates (`.forge.py` or `.html`).
- `routes/web.py` & `routes/api.py` — Route definitions using `craft.facades.Route`.

## 3. FACADES & DEPENDENCY INJECTION
Import facades directly:
```python
from craft.facades import Route, DB, Auth, AntiSpam, View, Cache, Firewall
```

## 4. FORM VALIDATION & ANTI-SPAM
- Validation:
  ```python
  from craft.validation.validator import Validator

  validator = Validator.make(data, {
      "email": ["required", "email"],
      "avatar": ["nullable", "image", "max_file_size:2048"],
      "website": ["nullable", "url"],
      "bio": ["required", "text", "no_html", "spam_free"],
  })
  if validator.fails():
      return redirect.back().with_errors(validator.errors()).with_input()
  ```
- Forge Templates:
  - Form Protection: `@csrf`, `@honeypot`, `@antispam`
  - Inline Errors: `@error('field_name') <span class="error">{{ message }}</span> @enderror`
  - Old Input: `value="{{ old('field_name', '') }}"`

## 5. GENERATOR CHEAT SHEET
- `python dev.py make:model <Name> [--migration]`
- `python dev.py make:controller <Name> [--resource]`
- `python dev.py make:request <Name>`
- `python dev.py make:resource <Name>`
- `python dev.py make:crud <Entity> --fields "title:string:required,body:text"`
- `python dev.py make:auth`
- `python dev.py agent:scaffold`
- `python dev.py agent:install <name>... | --all`
"""


def llms_txt_content() -> str:
    return """# Craft Engine
> High-performance async Python web framework designed with Laravel elegance, Active Record ORM, Typer CLI, and native AI coding agent ergonomics.

## Core Architectural Primitives
- **Active Record ORM**: Async Python models inheriting `craft.orm.model.Model` with fluent query builder, relationships, casts, and soft deletes.
- **Facades**: Global static accessors (`Route`, `DB`, `Auth`, `AntiSpam`, `Cache`, `Firewall`, `View`).
- **Forge Template Engine**: High-velocity server-rendered views supporting `@extends`, `@section`, `@csrf`, `@honeypot`, `@antispam`, and `@error('field')`.
- **Form Validation & AntiSpam**: Zero-dependency `Validator` supporting 30+ rules (`required`, `email`, `url`, `file`, `image`, `mimes`, `max_file_size`, `alpha_spaces`, `no_html`, `spam_free`, `honeypot`), with `MessageBag` and `redirect.back().with_errors()`.
- **Forward-Only Database Evolution**: Schema safety enforced by `python dev.py migrate`. Banned destructive operations protect data persistence.

## Key CLI Commands (`python dev.py <cmd>`)
- `python dev.py serve [--port 9000]` — Launch ASGI development server.
- `python dev.py migrate` — Apply forward-only schema migrations.
- `python dev.py make:model <Name> [-m]` — Generate Active Record model and optional migration.
- `python dev.py make:controller <Name> [--resource]` — Generate HTTP controller.
- `python dev.py make:request <Name>` — Generate FormRequest validator.
- `python dev.py make:crud <Entity> --fields "<spec>"` — Generate full vertical slice (model, migration, controller, request, resource, views, routes).
- `python dev.py make:auth` — Scaffold login, registration, dashboard, requests, and Forge templates.
- `python dev.py agent:scaffold` — Bootstrap AI agent context files (.cursorrules, llms.txt, AGENTS.md, mcp.json).
- `python dev.py agent:list` / `python dev.py agent:install <name>... | --all` — Install development agents, skills and commands into `.claude/`.

## Documentation Links
- [Complete Architecture Guide](llms-full.txt)
- [Form Validation & AntiSpam](documentation/forms_and_validation.md)
- [CLI Reference](documentation/cli.md)
- [AI Agents Standard](documentation/ai_agents.md)
"""


def llms_full_txt_content() -> str:
    return """# Craft Engine — Full Specification for LLMs & AI Coding Agents

Craft Engine is a full-stack Python web framework with Laravel-like syntax, async ASGI runtime, Active Record ORM, and integrated security and AI tooling.

---

## 1. Active Record Models
File location: `app/Models/<ModelName>.py`
```python
from craft.orm.model import Model

class Article(Model):
    __table__ = "articles"
    fillable = ["title", "slug", "body", "author_id", "is_published"]
    casts = {"is_published": "boolean"}

    def author(self):
        return self.belongs_to("app.Models.User.User", "author_id")
```

Querying:
```python
# Create
article = Article.create({"title": "Hello", "slug": "hello", "body": "World"})

# Retrieve
published = Article.where("is_published", True).order_by("created_at", "desc").get()
first = Article.find(1)
```

---

## 2. HTTP Routing & Controllers
File location: `routes/web.py`
```python
from craft.facades import Route
from app.Http.Controllers.ArticleController import ArticleController

Route.get("/articles", [ArticleController, "index"]).name("articles.index")
Route.get("/articles/{id}", [ArticleController, "show"]).name("articles.show")
Route.post("/articles", [ArticleController, "store"]).middleware("auth", "throttle").name("articles.store")
```

Controller implementation: `app/Http/Controllers/ArticleController.py`
```python
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.validation.validator import Validator
from app.Models.Article import Article

class ArticleController(Controller):
    def index(self, request):
        articles = Article.all()
        return self.view("articles.index", {"articles": articles})

    def store(self, request):
        validator = Validator.make(request.all(), {
            "title": ["required", "string", "min:3", "max:255"],
            "body": ["required", "text", "no_html", "spam_free"],
        })
        if validator.fails():
            return redirect.back().with_errors(validator.errors()).with_input()

        Article.create(validator.validated())
        return redirect(route="articles.index")
```

---

## 3. Forge Views & Validation Errors
File location: `resources/views/articles/create.forge.py`
```html
@extends("layouts.app")

@section("content")
<form action="/articles" method="POST">
    @csrf
    @honeypot

    <div>
        <label>Title</label>
        <input type="text" name="title" value="{{ old('title', '') }}">
        @error('title')
            <p class="error">{{ message }}</p>
        @enderror
    </div>

    <div>
        <label>Body</label>
        <textarea name="body">{{ old('body', '') }}</textarea>
        @error('body')
            <p class="error">{{ message }}</p>
        @enderror
    </div>

    <button type="submit">Publish</button>
</form>
@endsection
```

---

## 4. AntiSpam & Security Subsystems
Craft Engine includes a built-in zero-dependency AntiSpam system:
- **Invisible Honeypot**: `@honeypot` emits hidden CSS-cloaked trap fields.
- **HMAC Time Traps**: Validates human interaction duration (rejects forms submitted under 2.5 seconds or older than 3 hours).
- **Spam Free Heuristics**: Rejects known spam phrases, disposable domains, and malicious markup.
- **Security Events**: Logs all suspicious attempts with IP and user-agent forensics.

---

## 5. Non-Regression & Release Laws (NR-01 to NR-07)
- **NR-01**: `pyproject.toml` version must strictly match `engine.__version__`. Release counter matches monotonic `rNNNNN`.
- **NR-02**: Banned CLI commands (`migrate:reset`, `migrate:refresh`, `migrate:fresh`, `db:wipe`, `db:drop`) must never be exposed or executed.
- **NR-03**: Forward-only migrations (`python dev.py migrate`). No destructive SQL operations.
- **NR-04**: `CHANGELOG.md` must document the current release with `## [X.Y.Z] rNNNNN` header and preserve `## [Unreleased]`.
- **NR-05**: Public Facades (`Route`, `DB`, `Auth`, `AntiSpam`, `View`, `Cache`, `Firewall`) must preserve container accessors and support test mocking.
- **NR-06**: Security & AntiSpam regression prevention: `antispam` singleton in container, Forge helpers registered.
- **NR-07**: Zero linter errors under `ruff check engine` and 100% test pass rate.
"""


def mcp_config_content() -> str:
    return """{
  "mcpServers": {
    "craft-engine": {
      "command": "python",
      "args": ["dev.py", "route:list"],
      "env": {
        "APP_ENV": "development"
      }
    }
  }
}
"""


def agents_md_content() -> str:
    return """# AGENTS.md — Contract for every contributor, human or model

> Loaded automatically by every AI coding agent session (.claude/rules/AGENTS.md).
> Full rationale: `LANGUAGE_AND_I18N_STANDARD.md` and `CRAFT_ENGINEERING_GOVERNANCE.md`.

**Stack:** Craft Engine (Python 3.11+, async-first) · **Team language:** pt-BR · **Code language:** English
**CLI:** `python dev.py <command>`
**Gate:** Forward-only migrations, banned destructive commands, clean ruff linter, pytest suite.

---

## The three rules that are never negotiable

**R1 — The codebase is English.** Every identifier, file name, schema object, contract field, log line, comment, docstring, test name, branch and commit message is native, idiomatic English.

**R2 — Zero hardcoded user-facing text.** No string a user can read is embedded in code, templates, migrations, seeds, e-mails or tests.

**R3 — Absolute Data Persistence.** NEVER execute destructive database commands (`migrate:fresh`, `migrate:reset`, `db:wipe`, `db:drop`). Schema evolution is strictly forward-only (`python dev.py migrate`).

---

## Behavioural rules for AI agents

1. **Never mirror the conversation language into the code.** The chat is in pt-BR. The output is English. Every time, including comments.
2. **Never comply silently with a rule-breaking request.**
3. **Never "match the existing style" of legacy non-English code.**
4. **Never assume framework parity.** Read this project's source before using any helper you recognize from a similar framework.
5. **Zero guessing: inspect the workspace first.** Ground every action in concrete workspace inspection before executing commands.
6. **Tests count as code.** English names, no hardcoded copy.
7. **One commit, one concern.** Conventional Commits, English imperative.
"""


def scaffold_agent_stack(base_path: str, force: bool = False) -> Dict[str, Any]:
    """Scaffold all AI Agent context files (.cursorrules, llms.txt, AGENTS.md, mcp.json)."""
    result: Dict[str, Any] = {"files": {}}

    # 1. .cursorrules in project root
    cursorrules_path = os.path.join(base_path, ".cursorrules")
    _write_file(cursorrules_path, cursorrules_content(), force=force)
    result["files"]["cursorrules"] = cursorrules_path

    # 2. llms.txt in project root & documentation/
    llms_root_path = os.path.join(base_path, "llms.txt")
    _write_file(llms_root_path, llms_txt_content(), force=force)
    result["files"]["llms_root"] = llms_root_path

    llms_docs_path = os.path.join(base_path, "documentation", "llms.txt")
    _write_file(llms_docs_path, llms_txt_content(), force=force)
    result["files"]["llms_docs"] = llms_docs_path

    # 3. llms-full.txt in project root & documentation/
    llms_full_root = os.path.join(base_path, "llms-full.txt")
    _write_file(llms_full_root, llms_full_txt_content(), force=force)
    result["files"]["llms_full_root"] = llms_full_root

    llms_full_docs = os.path.join(base_path, "documentation", "llms-full.txt")
    _write_file(llms_full_docs, llms_full_txt_content(), force=force)
    result["files"]["llms_full_docs"] = llms_full_docs

    # 4. .agents/mcp.json
    mcp_path = os.path.join(base_path, ".agents", "mcp.json")
    _write_file(mcp_path, mcp_config_content(), force=force)
    result["files"]["mcp"] = mcp_path

    # 5. .claude/rules/AGENTS.md
    claude_agents_md = os.path.join(base_path, ".claude", "rules", "AGENTS.md")
    if not os.path.exists(claude_agents_md) or force:
        _write_file(claude_agents_md, agents_md_content(), force=force)
    result["files"]["agents_md"] = claude_agents_md

    # 6. .agents/rules/AGENTS.md pointer
    agents_pointer = os.path.join(base_path, ".agents", "rules", "AGENTS.md")
    pointer_content = "# AGENTS.md\n\nThe contract is a single file, loaded automatically by every Claude Code session:\n\n> **`.claude/rules/AGENTS.md`**\n"
    if not os.path.exists(agents_pointer) or force:
        _write_file(agents_pointer, pointer_content, force=force)
    result["files"]["agents_pointer"] = agents_pointer

    # 7. Development agents, skills, commands and references in .claude/
    result["catalog"] = agent_catalog.install(base_path, force=force)

    return result

# Introduction to Craft Engine

Craft Engine is a modern, full-stack MVC backend framework that brings expressive conventions, developer ergonomics, and batteries-included design to the Python ecosystem. Built on top of **Starlette** (the ASGI HTTP layer), its own multi-driver database layer and **Craft ORM** (SQLite, PostgreSQL, and MySQL with the same SQL), and **Jinja2** (preprocessed as the **Forge** engine), Craft Engine makes it easy to construct robust APIs and server-rendered web applications.

---

## Core Philosophy

1. **Convention over Configuration**: files go in specific directories, classes adhere to consistent name patterns, and dependencies resolve automatically.
2. **Developer Ergonomics**: Powerful command-line tooling, dynamic facades, and automatic dependency injection minimize boilerplate.
3. **Concurrent by default**: the synchronous middleware and controller chain runs on a thread pool, with each request borrowing a pooled database connection and returning it at the end — so one worker process overlaps requests instead of serving them one at a time. Async controller actions are awaited natively, and dependencies boot lazily. See [Deployment](deployment.md#concurrency) for the numbers and how to scale with `--workers`.
4. **Nothing decorative**: a promise the framework cannot keep is removed rather than faked. Unknown middleware aliases, unknown route names and unknown authorization abilities all fail loudly instead of silently doing nothing. [`CRAFT_ENGINE.md`](../CRAFT_ENGINE.md) keeps an explicit list of what is *not* built.

---

## Directory Structure

An out-of-the-box Craft project follows this standard layout:

```
project/
├── app/                        # Application Code
│   ├── Http/
│   │   ├── Controllers/        # Request handlers (Actions)
│   │   ├── Middleware/         # HTTP request/response middleware
│   │   ├── Requests/           # Typed validation requests (FormRequest)
│   │   └── Resources/          # API JSON transformers
│   ├── Models/                 # ActiveRecord database entities (Craft ORM)
│   ├── Policies/               # Gate authorization policy classes
│   ├── Providers/              # Service Providers for DI binding
│   └── Services/               # Custom business logic layer
├── bootstrap/app.py            # Builds the container, registers providers
├── config/                     # Configuration Files (env merged)
├── database/                   # Migrations, Seeders, and Factories
├── engine/                     # The framework itself — imported as craft.*
├── plugins/                    # Legacy plugins (deprecated; use app/plugins extensions)
├── public/index.py             # Front controller (ASGI entrypoint)
├── resources/
│   ├── lang/                   # Translation catalog
│   └── views/                  # HTML templates (Forge)
├── routes/                     # Route maps (web.py, api.py, console.py)
├── storage/                    # File uploads, cache, logs
├── tests/                      # pytest suite
└── dev.py                      # CLI command runner
```

> **`engine/` vs `craft.*`** — the framework lives on disk in `engine/`, but you
> never import it by that name. It registers `craft` as its public import alias
> at startup, so application code always writes `from craft.orm.model import
> Model`. Treat `engine/` as internal: read it to understand the framework,
> import `craft.*` to use it.

---

## Getting Started

### Prerequisites

- Python 3.14 or newer
- Docker & Docker Compose — optional, only for the PostgreSQL setup

### Installation & Run

The default database is SQLite, so no database server is needed:

1. Clone your project repository and install: `pip install -e ".[dev]"`.
2. Copy the environment file: `cp .env.example .env`.
3. Generate the key that signs session cookies: `python dev.py key:generate`.
4. Create and seed the schema: `python dev.py migrate --seed`.
5. Serve it: `python dev.py serve` — the app is at `http://127.0.0.1:9000`.

Or with Docker, which brings up the app and PostgreSQL together:

```bash
docker compose up -d --build
```

Access it at `http://localhost:9000`.

# The dev CLI

```bash
python dev.py <command>
```

Colon-separated commands work, and so does the plain form: `migrate:status` and
`migrate status` are the same command.

## Migrations

| Command | What it does |
|---|---|
| `migrate` | Apply pending migrations |
| `migrate --step N` | Apply only the first N pending |
| `migrate --pretend` | Print what would run, touching nothing |
| `migrate --seed` | Migrate, then run the DatabaseSeeder |
| `migrate:status` | Which migrations ran, and in which batch |
| `migrate:rollback` | Refused under absolute data persistence |
| `migrate:reset` | Refused under absolute data persistence |
| `migrate:refresh` | Refused under absolute data persistence |
| `migrate:fresh` | Refused under absolute data persistence |
| `migrate:install` | Create the migrations table only |

> **Safety Notice**: Craft Engine enforces **Absolute Data Persistence**. Destructive commands (`migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db wipe`) are strictly prohibited in production, test, and automated agent environments. See [Database Safety](database_safety.md).

## Database

| Command | What it does |
|---|---|
| `db seed` | Run `DatabaseSeeder` |
| `db seed --class UserSeeder` | Run one seeder |
| `db show` | Connection, driver, host, database |
| `db tables` | List tables |
| `db ping` | Verify the connection; non-zero exit on failure |
| `db wipe --force` | Drop every table *(Banned in persistence-first & automated agent workflows)* |

`db wipe` refuses to run without `--force`.

## Generators

| Command | Creates |
|---|---|
| `make model Product` | `app/Models/Product.py` |
| `make model Product -m` | Model plus a create migration |
| `make controller Product` | `app/Http/Controllers/ProductController.py` |
| `make controller Product -r` | Controller with index/show/store/update/destroy |
| `make migration create_products_table` | Timestamped migration |
| `make migration add_color_to_products_table` | An alter migration |
| `make middleware EnsureAdmin` | `app/Http/Middleware/` |
| `make request StoreProduct` | FormRequest |
| `make resource Product` | API resource |
| `make job SendEmail` | Queued job |
| `make event OrderPlaced` | Event |
| `make listener NotifyTeam` | Listener |
| `make policy Product` | Policy |
| `make seeder Product` | Seeder |
| `make service Billing` | Plain service class |
| `make auth [--views] [-f]` | Full authentication stack (Controller, FormRequests, Forge views, routes) |
| `make admin [-f]` | RBAC admin panel (controllers, Role/Permission/Group models, RBAC migration, Forge views, `/admin/*` routes, `config/auth.py` model entries) |

Names are normalised: `service_order`, `service-order` and `ServiceOrder` all
produce `ServiceOrder`. Suffixes are added once — `make controller Product` and
`make controller ProductController` both give `ProductController`.

Generators refuse to overwrite. Pass `--force` when you mean it.

Migration names drive the stub: `create_*_table` produces a create migration and
`add_*_to_*_table` produces an alter migration, with the table inferred.

## Routes

```bash
python dev.py route list
python dev.py route list --method POST
python dev.py route list --path /api
python dev.py route list --json
```

The table shows the ordered global middleware stack plus each route's declared
middleware. `--json` returns `global_middleware` and a `routes` array with
`method`, `uri`, `name`, and `middleware` fields for tooling and agents.

## Queue

```bash
python dev.py queue work
python dev.py queue work --queue emails
python dev.py queue work --once
```

See [Queues and events](queues_events.md).

## Cache

```bash
python dev.py cache clear
```

## Firewall (WAF) & Security Audit

| Command | What it does |
|---|---|
| `firewall list` | List IP whitelist/blacklist rules and reputation scores |
| `firewall allow <ip>` | Add an IP address to the trusted whitelist |
| `firewall block <ip> [-r reason]` | Add an IP address to the permanent blacklist |
| `security audit [--limit N]` | Display recent authentication attempts and honeypot events |

```bash
python dev.py firewall list
python dev.py firewall allow 192.168.1.100
python dev.py firewall block 203.0.113.55 -r "Port scanner detected"
python dev.py security audit --limit 50
```

## AI Coding Agents & Discovery

Craft Engine is optimized for autonomous AI coding agents (Cursor, Claude Code, Windsurf, AGY):

| Command | What it does |
|---|---|
| `agent:scaffold [-f]` | Bootstrap AI context files (`.cursorrules`, `llms.txt`, `llms-full.txt`, `.agents/mcp.json`) and install the whole agent catalog into `.claude/` |
| `agent:rules` | Alias for `agent:scaffold` |
| `agent:list [--kind K]` | List catalog entries: `agent`, `skill`, `command`, `reference` |
| `agent:install NAME... [-f]` | Install named agents, skills or commands (shared references always come along) |
| `agent:install --all [-f]` | Install the whole catalog |

```bash
python dev.py agent:scaffold
python dev.py agent:list --kind agent
python dev.py agent:install code-reviewer test-driven-development ship
```

Installs refuse to overwrite an existing entry without `--force`, and check every
conflict before writing anything. See [AI Agents](ai_agents.md#development-agent-catalog).

## Application


| Command | What it does |
|---|---|
| `serve` | Development server (`--host`, `--port`, `--no-reload`) |
| `tinker` | Interactive shell with the app booted |
| `about` | Environment, debug, Python, database, cache, queue |
| `key:generate` | Generate `APP_KEY` and write it to `.env` |

`tinker` gives you `app`, `db` and the facades:

```python
>>> from app.Models.User import User
>>> User.query().count()
3
```

## Exit codes

Commands exit non-zero on failure, so they compose in scripts and CI:

```bash
python dev.py db ping && python dev.py migrate
```

## Adding a command

`dev` is built with [Typer](https://typer.tiangolo.com/). Add commands in
`engine/cli/app.py`:

```python
@cli.command("stats")
def stats():
    """Show application statistics."""
    app = get_app()
    total = app.make("db").statement("SELECT COUNT(*) AS n FROM users").fetchone()
    echo(f"Users: {total['n']}")
```

Use `get_app()` to boot the application lazily — importing it at module level
would slow down every command, including `--help`.

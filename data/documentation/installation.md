# Installation

## Requirements

- **Python 3.14 or newer.** The suite is validated on 3.14.
- A database. **SQLite is the default** and ships with Python — no server
  needed. PostgreSQL and MySQL are opt-in.

## Setup

```bash
git clone <repository-url> my-app
cd my-app
pip install -e ".[dev]"
```

`[dev]` adds `pytest` and `httpx`. For a production install, drop it.

Optional extras:

```bash
pip install -e ".[mysql]"   # PyMySQL
pip install -e ".[redis]"   # Redis cache store
```

## Configure

```bash
cp .env.example .env
python dev.py key:generate
```

`key:generate` writes `APP_KEY`, which signs session cookies. Skip it and the
framework falls back to a random per-process key — sessions work, but they do
not survive a restart and are not shared between workers.

`.env.example` ships with SQLite, so a fresh checkout needs no database server:
the file `storage/database.sqlite` is created on the first migrate. To use
PostgreSQL or MySQL instead, uncomment and fill the server block:

```ini
DB_CONNECTION=pgsql          # sqlite | pgsql | mysql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=my_app
DB_USERNAME=postgres
DB_PASSWORD=secret
```

`DB_DATABASE` doubles as the SQLite file path, so only set it when using a
server driver.

## Create the schema

```bash
python dev.py migrate --seed
```

Confirm the connection first if you like:

```bash
python dev.py db ping
python dev.py db show
```

A new project seeds nothing. There are no accounts until you create them:
run `craft make:auth` for a user model and sign-in, then register through
`/register` or create users from `craft tinker`.

## Run

```bash
python dev.py serve
```

The application is at `http://127.0.0.1:9000`. Use `--host`, `--port` and
`--no-reload` to change how it runs.

## Docker

`docker-compose.yml` brings up the app and PostgreSQL together:

```bash
docker compose up -d --build
```

- Application: `http://localhost:9000`
- PostgreSQL: `localhost:5499` (user `craft`, database `craft_db`)

Run the suite inside the container to check the minimum Python version:

```bash
docker exec framework python -m pytest
```

The database uses a named volume, so recreating the container keeps your data.

## Verify

```bash
python -m pytest
```

## Directory layout

```
app/                     Your application code
  Http/Controllers/      Controllers
  Http/Middleware/       Middleware
  Http/Requests/         FormRequests
  Http/Resources/        JSON transformers
  Models/                Craft ORM models
  Policies/ Events/ Listeners/ Jobs/ Providers/ Services/
bootstrap/app.py         Builds the container, registers providers, mounts the kernel
config/                  app, auth, cache, database, logging, queue, session
database/                migrations/ seeders/ factories/
public/index.py          Front controller (`application = asgi_app`)
resources/views/         Forge templates
resources/lang/          Translation catalog
routes/                  web.py, api.py, console.py
engine/                  The framework itself, imported as craft.*
storage/                 Logs, cache, sessions
tests/                   Test suite
dev.py                 CLI entry point
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'craft'`** (or `'engine'`) — run commands
from the project root, or install with `pip install -e .`.

**`psycopg2` errors on connect** — check `db ping` output and confirm the
database exists. `dev` cannot create the database itself.

**Passwords hash slowly, or a bcrypt warning appears** — `passlib` breaks with
bcrypt 4.1+. The dependency is pinned to `<4.1`; if your environment has a newer
one, the framework falls back to PBKDF2 rather than failing.

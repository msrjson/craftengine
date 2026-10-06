# Installation

## Requirements

- **Python 3.14 or newer.** The suite is validated on 3.14.
- A database. **SQLite is the default** and ships with Python — no server
  needed. PostgreSQL and MySQL are opt-in.
- Git for installing pinned source releases and running the application change guard.

## Start an application

Commercial applications use the engine as a pinned package dependency. Each
application owns its code and repository; a product feature does not authorize
editing the framework. Choose the release tag approved for the application:

```bash
python -m pip install "craft[dev] @ git+https://github.com/msrjson/craftengine.git@<approved-tag>#subdirectory=data"
craft new my-app
cd my-app
```

`[dev]` adds the development tools. For production, omit that extra. Record the
same approved tag in the application's dependency manifest or image build and
adopt that pin file with `craft engine adopt <approved-tag> --pin <pin-file>`.
The generated engine lock records the release used to create the project;
the lock does not install the dependency by itself.

Initialize the application's own Git repository and create its initial commit
before assigning feature tasks. Exclude secrets and runtime data from version
control. New projects include `AGENTS.md` and a baseline-based engine change
guard; see [architecture.md](architecture.md#maintaining-commercial-applications-with-agents).

Optional extras:

```bash
python -m pip install "craft[mysql] @ git+https://github.com/msrjson/craftengine.git@<approved-tag>#subdirectory=data"
python -m pip install "craft[redis] @ git+https://github.com/msrjson/craftengine.git@<approved-tag>#subdirectory=data"
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

The framework development repository's `docker-compose.yml` brings up the
framework and PostgreSQL together. A generated application supplies its own
deployment configuration and installs the approved engine package there:

```bash
docker compose up -d --build
```

- Application: `http://localhost:9000`
- PostgreSQL: `localhost:5499` (user `craft`, database `craft_db`)

## Contributing to the engine

Cloning the canonical framework repository and installing it with
`pip install -e ".[dev]"` is for framework development. That editable checkout
is separate from commercial application repositories and their feature tasks.

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

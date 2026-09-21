"""The `dev` command line interface for Craft Framework.

Migrations, seeding, generators, routing inspection,
queue workers and the development server.

Category: Core Framework (CLI).
Relations:
  - Invoked by `dev.py`, which pre-splits `group:subcommand` tokens (e.g.
    `migrate:status`) into `group subcommand` before handing off to Typer.
  - Generators live in `engine/cli/generators.py`.
References:
  - Guide: `documentation/cli.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any, List, Optional

import typer

cli = typer.Typer(
    name="dev",
    help="Craft Framework console.",
    no_args_is_help=True,
    add_completion=False,
)

make_app = typer.Typer(name="make", help="Generate framework classes.", no_args_is_help=True)
migrate_app = typer.Typer(name="migrate", help="Run database migrations.", invoke_without_command=True)
db_app = typer.Typer(name="db", help="Database utilities.", no_args_is_help=True)
queue_app = typer.Typer(name="queue", help="Queue workers.", no_args_is_help=True)
schedule_app = typer.Typer(name="schedule", help="Scheduled tasks.", no_args_is_help=True)
route_app = typer.Typer(name="route", help="Routing utilities.", no_args_is_help=True)
cache_app = typer.Typer(name="cache", help="Cache utilities.", no_args_is_help=True)
plugin_app = typer.Typer(name="plugin", help="Plugin discovery and lifecycle.", no_args_is_help=True)
role_app = typer.Typer(name="role", help="RBAC role management.", no_args_is_help=True)
permission_app = typer.Typer(name="permission", help="RBAC permission management.", no_args_is_help=True)
group_app = typer.Typer(name="group", help="Group management (team-level access).", no_args_is_help=True)
user_app = typer.Typer(name="user", help="User management.", no_args_is_help=True)
firewall_app = typer.Typer(name="firewall", help="WAF & IP reputation management.", no_args_is_help=True)
security_app = typer.Typer(name="security", help="Security audit logs and alerts.", no_args_is_help=True)
docs_app = typer.Typer(name="docs", help="Documentation site.", no_args_is_help=True)
agent_app = typer.Typer(name="agent", help="AI Agent discovery and scaffolding.", no_args_is_help=True)
msr_app = typer.Typer(name="msr", help="MSR JSON manifest (/.well-known/msr.json).", no_args_is_help=True)

cli.add_typer(make_app)
cli.add_typer(migrate_app)
cli.add_typer(db_app)
cli.add_typer(queue_app)
cli.add_typer(schedule_app)
cli.add_typer(route_app)
cli.add_typer(cache_app)
cli.add_typer(plugin_app)
cli.add_typer(role_app)
cli.add_typer(permission_app)
cli.add_typer(group_app)
cli.add_typer(user_app)
cli.add_typer(firewall_app)
cli.add_typer(security_app)
cli.add_typer(docs_app)
cli.add_typer(agent_app)
cli.add_typer(msr_app)



# -- application bootstrap ------------------------------------------------------

_app_instance: Any = None


def base_path() -> str:
    return os.getcwd()


def get_app(boot_http: bool = False) -> Any:
    """Boot (once) and return the Craft application."""
    global _app_instance
    if _app_instance is not None:
        return _app_instance

    if base_path() not in sys.path:
        sys.path.insert(0, base_path())

    import engine  # registers the `craft.*` module aliases  # noqa: F401

    if boot_http:
        from bootstrap.app import app as booted
    else:
        from bootstrap.app import create_app

        booted = create_app()

    _app_instance = booted
    return _app_instance


def get_migrator() -> Any:
    from engine.migrations.migrator import Migrator

    return Migrator(get_app())


def echo(message: str, color: Optional[str] = None, bold: bool = False) -> None:
    if color or bold:
        typer.echo(typer.style(message, fg=color, bold=bold))
    else:
        typer.echo(message)



# -- migrate --------------------------------------------------------------------

@migrate_app.callback()
def migrate(
    ctx: typer.Context,
    step: Optional[int] = typer.Option(None, help="Only run the first N pending migrations."),
    pretend: bool = typer.Option(False, help="Print what would run without touching the database."),
    seed: bool = typer.Option(False, help="Run the DatabaseSeeder afterwards."),
) -> None:
    """Run all pending migrations."""
    if ctx.invoked_subcommand is not None:
        return

    migrator = get_migrator()
    migrator.run(step=step, pretend=pretend)
    for note in migrator.notes:
        echo(note, "green")

    if seed:
        _run_seeder("DatabaseSeeder")


@contextmanager
def _destructive_guard() -> Iterator[None]:
    """Turn a refused destructive operation into a clean CLI failure."""
    from engine.migrations.safety import DestructiveOperationRefused

    try:
        yield
    except DestructiveOperationRefused as refused:
        echo(f"Refused: {refused.params['operation']} on permanent database "
             f"'{refused.params['database']}'. Only in-memory SQLite, '*_test' or "
             "DB_DISPOSABLE_DATABASES may be wiped (NR-02).", "red")
        raise typer.Exit(code=1) from refused


@migrate_app.command("rollback")
def migrate_rollback(step: int = typer.Option(1, help="How many batches to revert.")) -> None:
    """Roll back the last batch of migrations."""
    migrator = get_migrator()
    migrator.rollback(step=step)
    for note in migrator.notes:
        echo(note, "yellow")


@migrate_app.command("reset")
def migrate_reset() -> None:
    """Roll back every migration."""
    migrator = get_migrator()
    with _destructive_guard():
        migrator.reset()
    for note in migrator.notes:
        echo(note, "yellow")


@migrate_app.command("refresh")
def migrate_refresh(seed: bool = typer.Option(False, help="Seed after refreshing.")) -> None:
    """Roll back and re-run every migration."""
    migrator = get_migrator()
    with _destructive_guard():
        migrator.refresh()
    for note in migrator.notes:
        echo(note, "green")
    if seed:
        _run_seeder("DatabaseSeeder")


@migrate_app.command("fresh")
def migrate_fresh(seed: bool = typer.Option(False, help="Seed after rebuilding.")) -> None:
    """Drop every table and re-run all migrations."""
    migrator = get_migrator()
    with _destructive_guard():
        migrator.fresh()
    for note in migrator.notes:
        echo(note, "green")
    if seed:
        _run_seeder("DatabaseSeeder")


@migrate_app.command("status")
def migrate_status() -> None:
    """Show which migrations have run."""
    rows = get_migrator().status()
    if not rows:
        echo("No migrations found.", "yellow")
        return

    echo(f"{'Ran?':<6} {'Batch':<7} Migration")
    echo("-" * 78)
    for row in rows:
        mark = "Yes" if row["ran"] else "No"
        batch = str(row["batch"] or "")
        echo(f"{mark:<6} {batch:<7} {row['migration']}")


@migrate_app.command("install")
def migrate_install() -> None:
    """Create the migration repository table."""
    get_migrator().ensure_repository()
    echo("Migration table created successfully.", "green")


# -- db -------------------------------------------------------------------------

def _run_seeder(name: str) -> None:
    from engine.seeding import run_seeder

    app = get_app()
    seeder = run_seeder(name, app)
    for note in getattr(seeder, "command_output", []):
        echo(note, "green")
    echo(f"Database seeding completed ({name}).", "green")


@db_app.command("seed")
def db_seed(
    seeder: str = typer.Option("DatabaseSeeder", "--class", help="Seeder class to run.")
) -> None:
    """Seed the database with records."""
    _run_seeder(seeder)


@db_app.command("show")
def db_show() -> None:
    """Show the active database connection."""
    app = get_app()
    db = app.make("db")
    config = app.make("config")
    name = config.get("database.default")
    settings = config.get(f"database.connections.{name}", {}) or {}

    echo(f"Connection : {name}")
    echo(f"Driver     : {db.driver}")
    echo(f"Host       : {settings.get('host', '-')}")
    echo(f"Port       : {settings.get('port', '-')}")
    echo(f"Database   : {settings.get('database', '-')}")

    dialect = db.dialect
    version = getattr(dialect, "version", None)
    if version is not None:
        from craft.orm.dialect import RECOMMENDED_POSTGRES, format_version

        echo(f"Server     : PostgreSQL {format_version(version)} "
             f"(recommended {format_version(RECOMMENDED_POSTGRES)}+)")
        advice = dialect.version_advice()
        if advice:
            echo(f"             {advice}", "red" if not dialect.meets_minimum else "yellow")


@db_app.command("ping")
def db_ping() -> None:
    """Verify the database connection is reachable."""
    try:
        db = get_app().make("db")
        db.statement("SELECT 1")
        echo(f"Connection OK ({db.driver}).", "green")
    except Exception as exc:
        echo(f"Connection FAILED: {exc}", "red")
        raise typer.Exit(code=1) from None


@db_app.command("extensions")
def db_extensions() -> None:
    """Show which PostgreSQL extensions are installed, and what each is for."""
    app = get_app()
    db = app.make("db")
    schema = app.make("schema")

    if not db.dialect.supports("extensions"):
        echo(f"The {db.driver!r} driver has no extensions.", "yellow")
        return

    installed = set(schema.installed_extensions())
    for name, purpose in sorted(schema.KNOWN_EXTENSIONS.items()):
        mark, colour = ("installed", "green") if name in installed else ("-", "yellow")
        echo(f"  {mark:>10}  {name:<12} {purpose}", colour)

    extra = installed - set(schema.KNOWN_EXTENSIONS)
    for name in sorted(extra):
        echo(f"  {'installed':>10}  {name:<12} (not used by the framework)")


@db_app.command("partitions")
def db_partitions(
    table: str = typer.Argument(..., help="The partitioned table."),
    ahead: int = typer.Option(3, help="How many months ahead to create."),
) -> None:
    """Create the upcoming partitions for a range-partitioned table.

    Schedule this. A range-partitioned table with no partition covering today
    rejects inserts, so the task is what keeps the table writable — not a
    tidiness measure.
    """
    created = get_app().make("schema").ensure_partitions(table, ahead=ahead)
    for name in created:
        echo(f"  ready  {name}", "green")
    echo(f"{len(created)} partition(s) present through {ahead} month(s) ahead.")


@db_app.command("locks")
def db_locks(
    key: str = typer.Argument(None, help="Explain one lock key instead of listing.")
) -> None:
    """Show the advisory locks currently held."""
    app = get_app()
    lock = app.make("lock")

    if not lock.supported():
        echo(f"The {app.make('db').driver!r} driver has no advisory locks.", "yellow")
        raise typer.Exit(code=1)

    if key:
        report = lock.explain(key)
        echo(f"  {report['key']}  ->  {report['id']}")
        for holder in report["holders"]:
            echo(f"      pid {holder['pid']}  granted={holder['granted']}")
        if not report["holders"]:
            echo("      not held", "green")
        return

    rows = app.make("db").statement(
        "SELECT pid, classid, objid, granted FROM pg_locks "
        "WHERE locktype = 'advisory' ORDER BY pid",
        read=True,
    ).fetchall()
    for row in rows:
        echo(f"  pid {row['pid']}  classid={row['classid']} objid={row['objid']} "
             f"granted={row['granted']}")
    echo(f"{len(rows)} advisory lock(s) held.")


@db_app.command("provision-role")
def db_provision_role(
    role: str = typer.Argument("craft_app", help="Name of the application role."),
    password: str = typer.Option(None, help="Password. Generated if omitted."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the SQL, run nothing."),
) -> None:
    """Create the non-superuser role that row-level security actually applies to.

    Policies do not apply to a superuser, and do not apply to a role granted
    BYPASSRLS — `FORCE ROW LEVEL SECURITY` only reaches the table's owner. So
    an application connecting as the role that ran the migrations sees every
    tenant's rows while each table reports itself protected. This creates the
    role that closes that gap, and refuses to hand back one that does not.

    Run it as an administrative user; connect the application as the result.
    """
    import secrets

    from craft.migrations.schema import _assert_table
    from craft.orm.connection import assert_schema_identifier

    app = get_app()
    db = app.make("db")

    if not db.dialect.supports("rls"):
        echo(f"The {db.driver!r} driver has no row-level security; there is no "
             f"role to provision.", "yellow")
        raise typer.Exit(code=1)

    # Interpolated, not bound — CREATE ROLE takes an identifier.
    _assert_table(role)
    schema = "public"
    assert_schema_identifier(schema)
    password = password or secrets.token_urlsafe(24)

    statements = [
        # NOBYPASSRLS is the point of the whole command.
        (f'CREATE ROLE "{role}" LOGIN NOBYPASSRLS PASSWORD %s', [password]),
        (f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"', []),
        (f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{role}"', []),
        (f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "{schema}" TO "{role}"', []),
        # Tables created by later migrations need the grant too, or the role
        # works until the next migration and then stops.
        (f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
         f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{role}"', []),
        (f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{schema}" '
         f'GRANT USAGE, SELECT ON SEQUENCES TO "{role}"', []),
    ]

    if dry_run:
        for sql, _ in statements:
            echo(f"  {sql.replace('%s', repr('<password>'))}")
        return

    exists = db.statement(
        "SELECT 1 AS present FROM pg_roles WHERE rolname = ?", [role], read=True
    ).fetchone()

    for index, (sql, params) in enumerate(statements):
        if index == 0 and exists is not None:
            echo(f"Role {role!r} already exists; granting only.", "yellow")
            password = None
            continue
        db.statement(sql, params)

    status = db.statement(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = ?", [role], read=True
    ).fetchone()
    if status is None or status["rolsuper"] or status["rolbypassrls"]:
        echo(f"Role {role!r} still bypasses row-level security — policies would "
             f"be inert under it. Not usable as the application role.", "red")
        raise typer.Exit(code=1)

    echo(f"Role {role!r} is subject to row-level security policies.", "green")
    if password:
        echo("\nPoint the application at it:", "green")
        echo(f"  DB_USERNAME={role}")
        echo(f"  DB_PASSWORD={password}")
        echo("\nShown once — it is not stored anywhere. Keep migrations running "
             "as the owning role, which is a separate credential.", "yellow")
    echo("\nVerify with: python dev.py db:audit-rls")


@db_app.command("audit-rls")
def db_audit_rls() -> None:
    """Fail if a table carrying `tenant_id` is not actually isolated.

    Meant for CI. The realistic way tenant isolation decays is a table added
    without `t.tenant_scoped()`: nothing errors, nothing looks wrong, and one
    table serves every tenant's rows to everyone. This is the check that
    notices before a customer does.
    """
    app = get_app()
    db = app.make("db")

    if not db.dialect.supports("rls"):
        echo(
            f"The {db.driver!r} driver has no row-level security, so there is "
            f"nothing to audit — and nothing isolating your tenants. Run this "
            f"against the PostgreSQL connection you deploy with.",
            "yellow",
        )
        raise typer.Exit(code=1)

    tenant = app.make("tenant")

    # The role first. Policies that cannot apply to the connecting role are
    # decoration, and every table below would report itself protected.
    status = tenant.enforcement(refresh=True)
    if status["enforced"]:
        echo(f"  role         {status['role']} — subject to policies", "green")
    else:
        echo(
            f"  ROLE         {status['role']} — {status['reason']}. Every policy "
            f"on this database is inert; connect the application as a role that "
            f"is neither a superuser nor granted BYPASSRLS.",
            "red",
        )

    report = tenant.audit()
    if not report:
        echo("No tenant-scoped tables found.", "yellow")
        raise typer.Exit(code=0 if status["enforced"] else 1)

    unprotected = [row for row in report if not row["protected"]]
    for row in report:
        if row.get("exempt"):
            echo(f"  carrier      {row['table_name']}  "
                 f"(tenant_id routes work, it does not scope rows)", "yellow")
        elif row["protected"]:
            echo(f"  ok           {row['table_name']}  "
                 f"({row['policies']} policy/policies, forced)", "green")
        else:
            echo(f"  UNPROTECTED  {row['table_name']}  "
                 f"(enabled={row['rls_enabled']}, forced={row['rls_forced']}, "
                 f"policies={row['policies']})", "red")

    if unprotected:
        echo(
            f"\n{len(unprotected)} of {len(report)} tenant-scoped table(s) are not "
            f"isolated. Add `t.tenant_scoped()` in a migration, or "
            f"`Schema.enable_row_level_security()` plus "
            f"`Schema.create_tenant_policy()` for an existing table.",
            "red",
        )
    elif status["enforced"]:
        echo(f"\nAll {len(report)} tenant-scoped table(s) are isolated.", "green")

    if unprotected or not status["enforced"]:
        raise typer.Exit(code=1)


@db_app.command("tables")
def db_tables() -> None:
    """List the tables in the current database."""
    app = get_app()
    db = app.make("db")
    if db.driver == "sqlite":
        sql = "SELECT name AS table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    elif db.driver == "postgresql":
        sql = "SELECT tablename AS table_name FROM pg_tables WHERE schemaname = current_schema() ORDER BY tablename"
    else:
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name"

    for row in db.statement(sql, read=True).fetchall():
        echo(f"  {row['table_name']}")


@db_app.command("wipe")
def db_wipe(
    confirm: bool = typer.Option(False, "--force", help="Required — this drops every table.")
) -> None:
    """Drop every table in the database."""
    if not confirm:
        echo("Refusing to wipe without --force.", "red")
        raise typer.Exit(code=1)
    with _destructive_guard():
        get_migrator().drop_all_tables()
    echo("Database wiped.", "yellow")


# -- make -----------------------------------------------------------------------

@make_app.command("model")
def make_model(
    name: str,
    migration: bool = typer.Option(False, "-m", "--migration", help="Also create a migration."),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Create a new Craft ORM model."""
    from engine.cli import generators

    try:
        path = generators.generate("model", name, base_path(), force=force)
    except FileExistsError as exc:
        echo(f"Model already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None

    echo(f"Model created: {path}", "green")

    if migration:
        table = generators.table_for(generators.studly(name))
        try:
            migration_path = generators.generate_migration(
                f"create_{table}_table", base_path(), table=table, create=True, force=force
            )
        except FileExistsError as exc:
            echo(f"Migration already exists: {exc}. Use --force to overwrite.", "red")
            raise typer.Exit(code=1) from None

        echo(f"Migration created: {migration_path}", "green")


@make_app.command("migration")
def make_migration(
    name: str,
    table: Optional[str] = typer.Option(None, help="Target table."),
    create: bool = typer.Option(True, help="Create a table (vs. alter one)."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing migration."),
) -> None:
    """Create a new migration file."""
    from engine.cli import generators

    try:
        path = generators.generate_migration(
            name, base_path(), table=table, create=create, force=force
        )
    except FileExistsError as exc:
        echo(f"Migration already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None

    echo(f"Migration created: {path}", "green")


@make_app.command("controller")
def make_controller(
    name: str,
    resource: bool = typer.Option(False, "-r", "--resource", help="Generate CRUD methods."),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Create a new controller."""
    from engine.cli import generators

    try:
        path = generators.generate("controller", name, base_path(), force=force, resource=resource)
    except FileExistsError as exc:
        echo(f"Controller already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None

    echo(f"Controller created: {path}", "green")


@make_app.command("crud")
def make_crud(
    entity: str,
    fields: str = typer.Option(
        "",
        "--fields",
        help='Field list: "name:type:rule1|rule2,other:type". Types: string, text, integer, big_integer, small_integer, float, boolean, decimal, date, datetime, json.',
    ),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run interactive field builder wizard."),
    pretend: bool = typer.Option(False, "--pretend", "--dry-run", help="Preview generated files without writing."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Generate a full CRUD slice: migration, model, controller, request, resource, views, and routes."""
    from engine.cli import crud_builder

    field_list = []
    if fields:
        try:
            field_list = crud_builder.parse_fields(fields)
        except ValueError as exc:
            echo(f"Error parsing fields: {exc}", "red")
            raise typer.Exit(code=1) from None
    elif interactive:
        echo(f"Interactive CRUD Wizard for [{entity}]:", bold=True)
        types_str = ", ".join(crud_builder.FIELD_TYPES.keys())
        while True:
            fname = typer.prompt("Field name (leave empty to finish)", default="", show_default=False).strip()
            if not fname:
                break
            ftype = typer.prompt(f"Field type ({types_str})", default="string").strip().lower()
            if ftype not in crud_builder.FIELD_TYPES:
                echo(f"Invalid type [{ftype}]. Allowed: {types_str}", "yellow")
                continue
            freq = typer.confirm("Is this field required?", default=False)
            field_list.append({
                "name": fname,
                "type": ftype,
                "nullable": not freq,
                "rules": ["required"] if freq else ["nullable"],
            })

    try:
        result = crud_builder.build_crud(
            entity, field_list, base_path(), force=force, pretend=pretend
        )
    except FileExistsError as exc:
        echo(f"A generated file already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None
    except ValueError as exc:
        echo(f"CRUD build error: {exc}", "red")
        raise typer.Exit(code=1) from None

    prefix = "[PREVIEW] Would generate" if pretend else "CRUD generated"
    color = "yellow" if pretend else "green"
    echo(f"{prefix} for [{result['entity']}]:", color, bold=True)
    for kind, path in result["files"].items():
        echo(f"  -> {kind:<20} {path}", color)


    if not pretend:
        echo("\nNext steps:", bold=True)
        echo("  1. Review the generated migration and run:", "cyan")
        echo("     python dev.py migrate", bold=True)
        echo("  2. Access the Admin UI at:", "cyan")
        echo(f"     http://127.0.0.1:9000/admin/{result['entity'].lower()}s", "cyan")
        echo("  3. Access the JSON REST API at:", "cyan")
        echo(f"     http://127.0.0.1:9000/api/v1/{result['entity'].lower()}s", "cyan")


@make_app.command("auth")
def make_auth(
    views_only: bool = typer.Option(False, "--views", help="Scaffold authentication Forge views only."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Scaffold complete authentication layer: Controller, Requests, Forge views, and routes."""
    from engine.cli import auth_scaffolder

    try:
        result = auth_scaffolder.build_auth(base_path(), views_only=views_only, force=force)
    except FileExistsError as exc:
        echo(f"Authentication file already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None

    echo("Authentication scaffolding generated successfully:", "green", bold=True)
    for kind, path in result["files"].items():
        echo(f"  -> {kind:<18} {path}", "green")

    echo("\nNext steps:", bold=True)
    echo("  1. Access the login screen at: http://127.0.0.1:9000/login", "cyan")
    echo("  2. Access the registration screen at: http://127.0.0.1:9000/register", "cyan")


def _simple_generator(kind: str, label: str):
    def command(name: str, force: bool = typer.Option(False, "--force")) -> None:
        from engine.cli import generators

        # A raw FileExistsError traceback tells the reader nothing about the
        # one thing they need to know: pass --force.
        try:
            path = generators.generate(kind, name, base_path(), force=force)
        except FileExistsError as exc:
            echo(f"{label} already exists: {exc}. Use --force to overwrite.", "red")
            raise typer.Exit(code=1) from None

        echo(f"{label} created: {path}", "green")

    command.__doc__ = f"Create a new {label.lower()}."
    return command


for _kind, _label in [
    ("middleware", "Middleware"),
    ("request", "Form request"),
    ("resource", "Resource"),
    ("job", "Job"),
    ("event", "Event"),
    ("listener", "Listener"),
    ("policy", "Policy"),
    ("seeder", "Seeder"),
    ("factory", "Factory"),
    ("service", "Service"),
]:
    make_app.command(_kind)(_simple_generator(_kind, _label))


# -- routes ---------------------------------------------------------------------

@route_app.command("list")
def route_list(
    method: Optional[str] = typer.Option(None, help="Filter by HTTP method."),
    path_filter: Optional[str] = typer.Option(None, "--path", help="Filter by URI substring."),
) -> None:
    """List every registered route."""
    app = get_app(boot_http=True)
    router = app.make("router")

    echo(f"{'METHOD':<16} {'URI':<44} NAME")
    echo("-" * 96)
    count = 0
    for route in router.routes:
        methods = "|".join(m for m in route.methods if m != "HEAD")
        if method and method.upper() not in route.methods:
            continue
        if path_filter and path_filter not in route.uri:
            continue
        echo(f"{methods:<16} {route.uri:<44} {route._name or '-'}")
        count += 1
    echo("-" * 96)
    echo(f"{count} route(s).")


# -- docs -----------------------------------------------------------------------

@docs_app.command("build")
def docs_build(
    output: str = typer.Option("public/docs", help="Where to write the site."),
    project: str = typer.Option("Craft Engine", help="Name shown in the sidebar."),
    base_url: str = typer.Option(
        "", "--base-url", help="Public URL of the site, e.g. https://craftengine.org/docs/. "
        "Given one, pages get a canonical URL, social metadata and a sitemap."
    ),
) -> None:
    """Render `documentation/` into a directory of static HTML.

    Same discovery, navigation and link rewriting the application's `/docs`
    routes use, so the published site cannot say something different from the
    one you get by running the framework.
    """
    from craft.support.docs import BrokenLink
    from craft.support.docs_site import DocsSiteBuilder

    # `base_path()`, not `get_app()`: rendering Markdown needs the files and a
    # parser, not a booted application with a database, a queue and every
    # service provider. Publishing documentation should not be able to fail
    # because a backend the docs merely describe is unreachable.
    base = base_path()
    docs_dir = os.path.join(base, "documentation")
    out_dir = output if os.path.isabs(output) else os.path.join(base, output)

    if not os.path.isdir(docs_dir):
        echo(f"No documentation directory at {docs_dir}.", "red")
        raise typer.Exit(code=1)

    try:
        written = DocsSiteBuilder(docs_dir, out_dir, project, base_url).build()
    except BrokenLink as exc:
        echo(f"Unknown catalog kind: {exc}", "red")
        raise typer.Exit(code=1) from None

    echo(f"Wrote {len(written)} file(s) to {out_dir}.", "green")


@docs_app.command("check")
def docs_check() -> None:
    """Fail if a guide links to a page that does not exist.

    An author never sees these: the file they linked to is open in front of
    them while they write the link. A reader sees a 404.
    """
    from craft.support.docs import DocsLibrary

    # No app boot — see the note in `docs:build`.
    docs_dir = os.path.join(base_path(), "documentation")
    broken = DocsLibrary(docs_dir).broken_links()

    if broken:
        for problem in broken:
            echo(f"  broken  {problem}", "red")
        echo(f"\n{len(broken)} broken link(s).", "red")
        raise typer.Exit(code=1)

    library = DocsLibrary(docs_dir)
    echo(f"{len(library.slugs())} page(s), no broken links.", "green")


# -- msr ------------------------------------------------------------------------

def _msr_manifest() -> dict:
    """Build the application's MSR JSON manifest, exiting with its code when incomplete."""
    from craft.http.msr import build_manifest
    from craft.support.msr import ManifestIncompleteError

    try:
        return build_manifest(get_app())
    except ManifestIncompleteError as exc:
        echo(f"{exc.code}: {exc.field} (see config/msr.py)", "red")
        raise typer.Exit(code=1) from None


@msr_app.command("show")
def msr_show() -> None:
    """Print the manifest served at `/.well-known/msr.json`."""
    from craft.http.msr import render_manifest

    echo(render_manifest(_msr_manifest()))


@msr_app.command("validate")
def msr_validate() -> None:
    """Validate the manifest against the canonical MSR JSON schema, fetched live.

    The schema is never copied into the project: a hand-kept copy drifts from
    the published one while claiming the same version.
    """
    from craft.support.msr import SCHEMA_URL, validate_manifest

    import urllib.error

    manifest = _msr_manifest()
    try:
        errors = validate_manifest(manifest)
    except ModuleNotFoundError:
        echo("DEPENDENCY_MISSING: jsonschema (pip install craft[msr])", "red")
        raise typer.Exit(code=1) from None
    except urllib.error.URLError as exc:
        echo(f"SCHEMA_UNREACHABLE: {SCHEMA_URL} ({exc})", "red")
        raise typer.Exit(code=1) from None
    for error in errors:
        echo(f"  {error}", "red")
    if errors:
        echo(f"{len(errors)} error(s) against {SCHEMA_URL}.", "red")
        raise typer.Exit(code=1)
    echo(f"valid: 0 errors against {SCHEMA_URL}.", "green")


# -- queue ----------------------------------------------------------------------

@queue_app.command("work")
def queue_work(
    queue: str = typer.Option("default", help="Queue name to process."),
    once: bool = typer.Option(False, help="Process a single job then exit."),
    listen: bool = typer.Option(
        False, "--listen", help="Wake on LISTEN/NOTIFY instead of polling (PostgreSQL)."
    ),
) -> None:
    """Process jobs from the queue."""
    import time

    app = get_app()
    manager = app.make("queue")

    # On the `sync` driver, `push()` runs jobs inline and nothing ever reaches
    # the `jobs` table — so the worker would print "processing" and spin
    # forever on an empty queue that can never fill.
    if manager.driver() == "sync":
        echo(
            "QUEUE_CONNECTION is 'sync': jobs run inline at dispatch time and "
            "never reach the queue, so there is nothing for a worker to do. "
            "Set QUEUE_CONNECTION=database to process jobs in the background.",
            "yellow",
        )
        raise typer.Exit(code=1)

    def drain() -> int:
        """Work the queue until it is empty, and say how many jobs ran."""
        done = 0
        while manager.work(queue):
            done += 1
            echo("Processed a job.", "green")
        return done

    if listen:
        from craft.queue.listener import Listener, queue_channel

        db = app.make("db")
        if not db.dialect.supports("listen_notify"):
            echo(
                f"--listen needs PostgreSQL; the {db.driver!r} driver has no "
                f"LISTEN/NOTIFY. Run without it to poll instead.",
                "red",
            )
            raise typer.Exit(code=1)

        echo(f"Waiting for jobs on the [{queue}] queue (LISTEN).", "green")
        drain()  # anything enqueued before the listener attached
        Listener(db, [queue_channel(queue)]).run(lambda channel, payload: drain())
        return

    echo(f"Processing jobs from the [{queue}] queue.", "green")
    from craft.support.shutdown import ShutdownSignal

    stop = ShutdownSignal(
        lambda name: echo(f"{name} received; finishing the current job.", "yellow")
    ).install()
    try:
        while not stop.requested:
            processed = manager.work(queue)
            if processed:
                echo("Processed a job.", "green")
            if once:
                break
            if not processed:
                # Waits on the stop event, so a deploy is not held up for a
                # second by a worker that happens to be idle.
                stop.wait(1)
    finally:
        stop.restore()
    if stop.requested:
        echo("Worker stopped cleanly.", "green")


@queue_app.command("failed")
def queue_failed(
    queue: str = typer.Option(None, help="Only this queue."),
    limit: int = typer.Option(50, help="How many to show."),
) -> None:
    """List jobs that exhausted their attempts, newest first."""
    records = get_app().make("queue").failed(queue, limit)
    if not records:
        echo("No failed jobs.", "green")
        return

    for record in records:
        echo(f"  {record.get('uuid')}  [{record.get('queue')}]  "
             f"{record.get('attempts')} attempt(s)  {record.get('failed_at')}")
        echo(f"      {str(record.get('exception') or '').splitlines()[0][:160]}", "yellow")
    echo(f"{len(records)} failed job(s).")


@queue_app.command("retry")
def queue_retry(
    job_uuid: str = typer.Argument(None, help="Job UUID, or omit with --all."),
    all_jobs: bool = typer.Option(False, "--all", help="Retry every failed job."),
) -> None:
    """Move failed jobs back onto their queue."""
    if not job_uuid and not all_jobs:
        echo("Give a job UUID, or --all to retry every failed job.", "red")
        raise typer.Exit(code=1)

    moved = get_app().make("queue").retry_failed(None if all_jobs else job_uuid)
    echo(f"Re-queued {moved} job(s).", "green" if moved else "yellow")


@queue_app.command("reclaim")
def queue_reclaim(
    retry_after: int = typer.Option(
        None, help="Seconds after which a reservation is assumed dead."
    ),
) -> None:
    """Free reservations held by workers that died mid-flight."""
    freed = get_app().make("queue").reclaim(retry_after)
    echo(f"Reclaimed {freed} job(s).", "green" if freed else "yellow")


# -- schedule -------------------------------------------------------------------

@schedule_app.command("list")
def schedule_list() -> None:
    """Show every registered scheduled task and when it runs."""
    from datetime import datetime

    tasks = get_app().make("schedule").tasks()
    if not tasks:
        echo("No scheduled tasks registered. Declare them in routes/console.py.", "yellow")
        return

    now = datetime.now()
    echo(f"{'EXPRESSION':<20} {'DUE NOW':<9} TASK")
    echo("-" * 96)
    for task in tasks:
        echo(f"{task.expression:<20} {'yes' if task.is_due(now) else 'no':<9} {task.name}")
    echo("-" * 96)
    echo(f"{len(tasks)} task(s).")


@schedule_app.command("run")
def schedule_run() -> None:
    """Run the tasks due this minute. Invoke from cron, every minute:

    * * * * * cd /app && python dev.py schedule run
    """
    ran = get_app().make("schedule").run_due()
    if not ran:
        echo("No scheduled tasks are due.", "yellow")
        return
    for name in ran:
        echo(f"Ran: {name}", "green")
    echo(f"{len(ran)} task(s) ran.")


@schedule_app.command("work")
def schedule_work() -> None:
    """Run the scheduler in the foreground, waking once a minute.

    A convenience for development and for containers with no cron daemon; a
    real deployment should prefer the single `schedule run` cron entry.
    """
    import time
    from datetime import datetime

    from craft.support.shutdown import ShutdownSignal

    manager = get_app().make("schedule")
    echo("Scheduler running. Ctrl-C to stop.", "green")
    stop = ShutdownSignal(
        lambda signal_name: echo(f"{signal_name} received; stopping.", "yellow")
    ).install()
    try:
        while not stop.requested:
            # Evaluate first, then sleep: sleeping first skipped anything due
            # in the minute the worker started.
            for name in manager.run_due():
                echo(f"Ran: {name}", "green")
            # Sleep to the top of the next minute so each minute is evaluated
            # once, waking early when a stop is requested.
            now = datetime.now()
            stop.wait(60 - now.second - now.microsecond / 1_000_000)
    finally:
        stop.restore()
    echo("Scheduler stopped cleanly.", "green")


# -- cache ----------------------------------------------------------------------

@cache_app.command("clear")
def cache_clear() -> None:
    """Flush the application cache."""
    get_app().make("cache").flush()
    echo("Application cache cleared.", "green")


# -- plugin ---------------------------------------------------------------------

@plugin_app.command("list")
def plugin_list() -> None:
    """List every plugin known to the application (DB or in-memory)."""
    manager = get_app().make("plugin")

    echo(f"{'SLUG':<24} {'NAME':<28} {'ENABLED':<9} PATH")
    echo("-" * 96)
    for entry in manager.installed():
        enabled = "Yes" if entry.get("enabled") else "No"
        echo(f"{entry.get('slug', '-'):<24} {entry.get('name', '-'):<28} {enabled:<9} {entry.get('path') or '-'}")


@plugin_app.command("enable")
def plugin_enable(slug: str) -> None:
    """Enable a plugin by slug."""
    manager = get_app().make("plugin")
    if not manager.enable(slug):
        echo(f"No such plugin: {slug}", "red")
        raise typer.Exit(code=1)
    echo(f"Plugin enabled: {slug}", "green")


@plugin_app.command("disable")
def plugin_disable(slug: str) -> None:
    """Disable a plugin by slug."""
    manager = get_app().make("plugin")
    if not manager.disable(slug):
        echo(f"No such plugin: {slug}", "red")
        raise typer.Exit(code=1)
    echo(f"Plugin disabled: {slug}", "green")


@plugin_app.command("sync")
def plugin_sync() -> None:
    """Discover plugins on disk and register newly found ones in the database."""
    manager = get_app().make("plugin")
    newly_registered = manager.sync(base_path())
    if newly_registered:
        echo(f"Registered {len(newly_registered)} new plugin(s): {', '.join(newly_registered)}", "green")
    else:
        echo("No new plugins found.", "yellow")


# -- role / permission (RBAC) ----------------------------------------------------

@role_app.command("list")
def role_list() -> None:
    """List every role and the permissions granted to it."""
    get_app()
    from app.Models.Role import Role

    roles = Role.query().get()
    echo(f"{'SLUG':<20} {'NAME':<24} PERMISSIONS")
    echo("-" * 96)
    for role in roles:
        perms = ", ".join(p.get_attribute("slug") for p in role.permissions().get()) or "-"
        echo(f"{role.get_attribute('slug'):<20} {role.get_attribute('name'):<24} {perms}")


@role_app.command("create")
def role_create(name: str, slug: str) -> None:
    """Create a role."""
    from app.Models.Role import Role

    get_app()
    Role.create({"name": name, "slug": slug})
    echo(f"Role created: {slug}", "green")


@role_app.command("grant")
def role_grant(role_slug: str, permission_slug: str) -> None:
    """Attach a permission to a role."""
    get_app()
    from app.Models.Role import Role
    from app.Models.Permission import Permission

    role = Role.query().where("slug", role_slug).first()
    if role is None:
        echo(f"No such role: {role_slug}", "red")
        raise typer.Exit(code=1)

    permission = Permission.query().where("slug", permission_slug).first()
    if permission is None:
        echo(f"No such permission: {permission_slug}", "red")
        raise typer.Exit(code=1)

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM permission_role WHERE role_id = ? AND permission_id = ?",
        [role.get_attribute("id"), permission.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"Role [{role_slug}] already has permission [{permission_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO permission_role (role_id, permission_id) VALUES (?, ?)",
        [role.get_attribute("id"), permission.get_attribute("id")],
    )
    echo(f"Granted [{permission_slug}] to role [{role_slug}].", "green")


@permission_app.command("list")
def permission_list() -> None:
    """List every permission."""
    get_app()
    from app.Models.Permission import Permission

    echo(f"{'SLUG':<24} NAME")
    echo("-" * 60)
    for permission in Permission.query().get():
        echo(f"{permission.get_attribute('slug'):<24} {permission.get_attribute('name')}")


@permission_app.command("create")
def permission_create(name: str, slug: str) -> None:
    """Create a permission."""
    from app.Models.Permission import Permission

    get_app()
    Permission.create({"name": name, "slug": slug})
    echo(f"Permission created: {slug}", "green")


# -- groups ----------------------------------------------------------------------
# A group grants access to a team rather than to one person at a time: it holds
# roles and/or permissions, and every member inherits them. See
# `documentation/authorization.md`.

def _require(model_cls, slug: str, label: str):
    """Fetch a record by slug or abort with a message naming what was missing."""
    record = model_cls.query().where("slug", slug).first()
    if record is None:
        echo(f"No such {label}: {slug}", "red")
        raise typer.Exit(code=1) from None
    return record


def _parse_conditions(raw: Optional[str]):
    """Validate `--conditions` before it reaches the database.

    A grant whose conditions cannot be parsed is refused at the CLI rather than
    stored: at check time an unreadable condition denies, so accepting it here
    would quietly create a grant that never works.
    """
    if raw is None:
        return None
    from engine.auth.conditions import ConditionError, dump, parse

    try:
        return dump(parse(raw))
    except ConditionError as exc:
        echo(f"Invalid --conditions: {exc}", "red")
        raise typer.Exit(code=1) from None


#: Shown wherever `--conditions` is accepted, so the syntax is one `--help` away.
CONDITIONS_HELP = (
    'Optional JSON conditions (ABAC), e.g. \'{"user_id": "@user.id"}\' for '
    '"only their own", or \'{"amount": {"lte": 10000}}\'. Omit for an '
    "unconditional grant."
)


@group_app.command("list")
def group_list() -> None:
    """List every group with its members, roles and direct permissions."""
    get_app()
    from app.Models.Group import Group

    echo(f"{'SLUG':<20} {'NAME':<24} {'MEMBERS':<8} ROLES / PERMISSIONS")
    echo("-" * 100)
    for group in Group.query().get():
        roles = ", ".join(r.get_attribute("slug") for r in group.roles().get())
        perms = ", ".join(p.get_attribute("slug") for p in group.permissions().get())
        granted = " / ".join(part for part in (roles, perms) if part) or "-"
        members = len(group.users().get())
        echo(
            f"{group.get_attribute('slug'):<20} {group.get_attribute('name'):<24} "
            f"{members:<8} {granted}"
        )


@group_app.command("create")
def group_create(name: str, slug: str, description: str = typer.Option("", help="Optional description.")) -> None:
    """Create a group."""
    from app.Models.Group import Group

    get_app()
    Group.create({"name": name, "slug": slug, "description": description or None})
    echo(f"Group created: {slug}", "green")


@group_app.command("add-user")
def group_add_user(group_slug: str, email: str) -> None:
    """Add a user to a group."""
    get_app()
    from app.Models.Group import Group
    from app.Models.User import User

    group = _require(Group, group_slug, "group")
    user = User.query().where("email", email).first()
    if user is None:
        echo(f"No such user: {email}", "red")
        raise typer.Exit(code=1) from None

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM group_user WHERE user_id = ? AND group_id = ?",
        [user.get_attribute("id"), group.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"[{email}] is already in group [{group_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO group_user (user_id, group_id) VALUES (?, ?)",
        [user.get_attribute("id"), group.get_attribute("id")],
    )
    echo(f"Added [{email}] to group [{group_slug}].", "green")


@group_app.command("remove-user")
def group_remove_user(group_slug: str, email: str) -> None:
    """Remove a user from a group."""
    get_app()
    from app.Models.Group import Group
    from app.Models.User import User

    group = _require(Group, group_slug, "group")
    user = User.query().where("email", email).first()
    if user is None:
        echo(f"No such user: {email}", "red")
        raise typer.Exit(code=1) from None

    db = get_app().make("db")
    result = db.statement(
        "DELETE FROM group_user WHERE user_id = ? AND group_id = ?",
        [user.get_attribute("id"), group.get_attribute("id")],
    )
    # Report what happened: "removed" for a membership that was never there
    # reads as success and hides a typo in the email or slug.
    if (getattr(result, "rowcount", 0) or 0) < 1:
        echo(f"[{email}] was not in group [{group_slug}]; nothing removed.", "yellow")
        return
    echo(f"Removed [{email}] from group [{group_slug}].", "green")


@group_app.command("grant-role")
def group_grant_role(
    group_slug: str,
    role_slug: str,
    conditions: Optional[str] = typer.Option(None, help=CONDITIONS_HELP),
) -> None:
    """Grant a role to every member of a group."""
    get_app()
    from app.Models.Group import Group
    from app.Models.Role import Role

    group = _require(Group, group_slug, "group")
    role = _require(Role, role_slug, "role")
    stored = _parse_conditions(conditions)

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM group_role WHERE group_id = ? AND role_id = ?",
        [group.get_attribute("id"), role.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"Group [{group_slug}] already grants role [{role_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO group_role (group_id, role_id, conditions) VALUES (?, ?, ?)",
        [group.get_attribute("id"), role.get_attribute("id"), stored],
    )
    echo(f"Group [{group_slug}] now grants role [{role_slug}].", "green")


@group_app.command("grant")
def group_grant_permission(
    group_slug: str,
    permission_slug: str,
    conditions: Optional[str] = typer.Option(None, help=CONDITIONS_HELP),
) -> None:
    """Grant a permission straight to a group, without inventing a role."""
    get_app()
    from app.Models.Group import Group
    from app.Models.Permission import Permission

    group = _require(Group, group_slug, "group")
    permission = _require(Permission, permission_slug, "permission")
    stored = _parse_conditions(conditions)

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM permission_group WHERE group_id = ? AND permission_id = ?",
        [group.get_attribute("id"), permission.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"Group [{group_slug}] already has permission [{permission_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO permission_group (group_id, permission_id, conditions) VALUES (?, ?, ?)",
        [group.get_attribute("id"), permission.get_attribute("id"), stored],
    )
    echo(f"Granted [{permission_slug}] to group [{group_slug}].", "green")


@user_app.command("grant")
def user_grant_permission(
    email: str,
    permission_slug: str,
    conditions: Optional[str] = typer.Option(None, help=CONDITIONS_HELP),
) -> None:
    """Grant a permission directly to one user.

    The exception every real system needs eventually: one person gets one extra
    permission, and inventing a single-member role for it is worse than
    recording it honestly.
    """
    get_app()
    from app.Models.Permission import Permission
    from app.Models.User import User

    user = User.query().where("email", email).first()
    if user is None:
        echo(f"No such user: {email}", "red")
        raise typer.Exit(code=1) from None
    permission = _require(Permission, permission_slug, "permission")
    stored = _parse_conditions(conditions)

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM permission_user WHERE user_id = ? AND permission_id = ?",
        [user.get_attribute("id"), permission.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"[{email}] already has permission [{permission_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO permission_user (user_id, permission_id, conditions) VALUES (?, ?, ?)",
        [user.get_attribute("id"), permission.get_attribute("id"), stored],
    )
    echo(f"Granted [{permission_slug}] to [{email}].", "green")


@user_app.command("access")
def user_access(email: str) -> None:
    """Show everything that authorizes a user: groups, roles, permissions.

    The answer to "why can this person do that?", which otherwise means reading
    five pivot tables by hand.
    """
    app = get_app()
    from app.Models.User import User

    user = User.query().where("email", email).first()
    if user is None:
        echo(f"No such user: {email}", "red")
        raise typer.Exit(code=1) from None

    access = app.make("access")
    echo(f"{email}", "green")
    echo(f"  groups      : {', '.join(access.groups(user)) or '-'}")
    echo(f"  roles       : {', '.join(access.roles(user)) or '-'}")

    slugs = access.permissions(user)
    echo(f"  permissions : {', '.join(slugs) or '-'}")
    for slug in slugs:
        for grant in access.explain(user, slug):
            condition = grant["conditions"] or "unconditional"
            echo(f"      {slug} via {grant['source']} ({condition})")


@user_app.command("assign-role")
def user_assign_role(email: str, role_slug: str) -> None:
    """Assign a role to a user by email."""
    get_app()
    from app.Models.User import User
    from app.Models.Role import Role

    user = User.query().where("email", email).first()
    if user is None:
        echo(f"No such user: {email}", "red")
        raise typer.Exit(code=1)

    role = Role.query().where("slug", role_slug).first()
    if role is None:
        echo(f"No such role: {role_slug}", "red")
        raise typer.Exit(code=1)

    db = get_app().make("db")
    already = db.statement(
        "SELECT 1 FROM role_user WHERE user_id = ? AND role_id = ?",
        [user.get_attribute("id"), role.get_attribute("id")],
        read=True,
    ).fetchone()
    if already:
        echo(f"User [{email}] already has role [{role_slug}].", "yellow")
        return

    db.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (?, ?)",
        [user.get_attribute("id"), role.get_attribute("id")],
    )
    echo(f"Assigned role [{role_slug}] to [{email}].", "green")


# -- firewall commands ---------------------------------------------------------

@firewall_app.command("list")
def firewall_list() -> None:
    """List all configured firewall IP rules and reputation scores."""
    app = get_app()
    db = app.make("db")
    rules = db.table("firewall_rules").get()
    if not rules:
        echo("No custom firewall rules configured.", "yellow")
        return

    echo(f"{'IP Address':<20} {'Status':<15} {'Score':<8} {'Reason'}", bold=True)
    echo("-" * 70)
    for r in rules:
        status_color = "green" if r.get("status") == "whitelist" else ("red" if r.get("status") == "blacklist" else "yellow")
        echo(
            f"{r.get('ip_address', ''):<20} "
            f"{typer.style(r.get('status', ''), fg=status_color):<24} "
            f"{r.get('reputation_score', 0):<8} "
            f"{r.get('blocked_reason') or '-'}"
        )


@firewall_app.command("allow")
def firewall_allow(ip: str) -> None:
    """Add an IP address to the trusted whitelist."""
    app = get_app()
    fw = app.make("firewall")
    fw.whitelist_ip(ip)
    echo(f"IP [{ip}] added to firewall whitelist.", "green")


@firewall_app.command("block")
def firewall_block(
    ip: str,
    reason: str = typer.Option("Manual administrator block", "--reason", "-r", help="Reason for blacklisting."),
) -> None:
    """Add an IP address to the permanent blacklist."""
    app = get_app()
    fw = app.make("firewall")
    fw.blacklist_ip(ip, reason=reason)
    echo(f"IP [{ip}] blacklisted. Reason: {reason}", "red")



# -- security audit commands ---------------------------------------------------

@security_app.command("audit")
def security_audit(limit: int = typer.Option(20, help="Number of audit logs to display.")) -> None:
    """Display recent authentication audit attempts and honeypot events."""
    app = get_app()
    db = app.make("db")
    logs = db.table("auth_audit_logs").order_by("id", "desc").limit(limit).get()
    if not logs:
        echo("No authentication audit logs recorded.", "yellow")
        return

    echo(f"{'Timestamp':<22} {'IP Address':<18} {'Username':<22} {'Result':<12} {'Reason'}", bold=True)

    echo("-" * 85)
    for log in logs:
        res = log.get("result", "")
        color = "green" if res == "SUCCESS" else ("magenta" if res == "HONEYPOT" else "red")
        echo(
            f"{str(log.get('created_at', ''))[:19]:<22} "
            f"{log.get('ip_address', ''):<18} "
            f"{log.get('username', ''):<22} "
            f"{typer.style(res, fg=color):<21} "
            f"{log.get('reason') or '-'}"
        )


# -- top-level commands ---------------------------------------------------------


@cli.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(9000, help="Bind port."),
    reload: bool = typer.Option(True, help="Reload on file changes."),
    workers: int = typer.Option(
        1, help="Worker processes. Ignored with --reload, which requires one."
    ),
) -> None:
    """Start the development server."""
    import uvicorn

    if workers < 1:
        echo("--workers must be at least 1.", "red")
        raise typer.Exit(code=1)

    # Uvicorn cannot reload and fork workers at the same time; saying so beats
    # silently serving with one worker after being asked for eight.
    if workers > 1 and reload:
        echo(
            f"--workers {workers} needs --no-reload (the reloader runs a single "
            "process). Serving with 1 worker.",
            "yellow",
        )
        workers = 1

    echo(
        f"Craft development server started on http://{host}:{port} "
        f"({workers} worker{'s' if workers > 1 else ''})",
        "green",
    )
    uvicorn.run(
        "bootstrap.app:asgi_app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
    )


@cli.command("tinker")
def tinker() -> None:
    """Open an interactive shell with the application booted."""
    import code

    app = get_app()
    context = {"app": app, "db": app.make("db")}
    available = ["app", "db"]

    try:
        from craft.facades import Auth, Cache, Config, DB, Event, Queue, Route, Schedule

        context.update({
            "Auth": Auth, "Cache": Cache, "Config": Config, "DB": DB,
            "Event": Event, "Queue": Queue, "Route": Route, "Schedule": Schedule,
        })
        available += ["Auth", "Cache", "Config", "DB", "Event", "Queue", "Route", "Schedule"]
    except Exception as exc:
        # The banner used to claim facades were available even when this import
        # had failed, leaving you typing `DB.` at a NameError.
        echo(f"Facades unavailable: {exc}", "yellow")

    code.interact(
        banner=f"Craft tinker — available: {', '.join(available)}.",
        local=context,
    )


@cli.command("about")
def about() -> None:
    """Show framework and environment information."""
    import platform

    app = get_app()
    config = app.make("config")
    echo("Craft Framework")
    # `APP_ENV`/`APP_DEBUG`, not `app.env`/`app.debug` — the config repository
    # keys entries by the module attribute name, so the short forms never
    # resolved and `about` always reported the defaults.
    echo(f"  Environment  : {config.get('app.APP_ENV', 'local')}")
    echo(f"  Debug        : {config.get('app.APP_DEBUG', False)}")
    echo(f"  Python       : {platform.python_version()}")
    echo(f"  Database     : {app.make('db').driver}")
    echo(f"  Cache        : {config.get('cache.default', 'array')}")
    echo(f"  Queue        : {config.get('queue.default', 'sync')}")


@cli.command("key:generate")
def key_generate() -> None:
    """Generate an application key and write it to `.env`."""
    import secrets

    key = "base64:" + secrets.token_urlsafe(32)
    env_path = os.path.join(base_path(), ".env")

    lines: List[str] = []
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()

    replaced = False
    for index, line in enumerate(lines):
        if line.startswith("APP_KEY="):
            lines[index] = f"APP_KEY={key}"
            replaced = True
            break
    if not replaced:
        lines.append(f"APP_KEY={key}")

    with open(env_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    echo(f"Application key set: {key}", "green")


@agent_app.command("scaffold")
def agent_scaffold(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Scaffold AI agent discovery and configuration files (.cursorrules, llms.txt, mcp.json)."""
    from engine.cli import agent_scaffolder

    try:
        result = agent_scaffolder.scaffold_agent_stack(base_path(), force=force)
    except FileExistsError as exc:
        echo(f"Agent file already exists: {exc}. Use --force to overwrite.", "red")
        raise typer.Exit(code=1) from None

    echo("AI Agent configuration generated successfully:", "green", bold=True)
    for kind, path in result["files"].items():
        echo(f"  -> {kind:<18} {path}", "green")

    echo("\nCraft Engine is now primed for AI coding agents (Cursor, Claude Code, Windsurf, AGY).", "cyan")


@agent_app.command("rules")
def agent_rules(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Alias for `dev.py agent scaffold`."""
    agent_scaffold(force=force)


@agent_app.command("list")
def agent_list(
    kind: Optional[str] = typer.Option(None, "--kind", "-k", help="agent, skill, command or reference."),
) -> None:
    """List the development agents, skills and commands the catalog can install."""
    from engine.cli import agent_catalog

    try:
        entries = agent_catalog.list_entries(kind)
    except ValueError as exc:
        echo(f"Unknown catalog kind: {exc}", "red")
        raise typer.Exit(code=1) from None
    for entry in entries:
        echo(f"  {entry.kind:<10} {entry.name:<36} {entry.description[:80]}")


@agent_app.command("install")
def agent_install(
    names: Annotated[Optional[List[str]], typer.Argument(help="Agent, skill or command names.")] = None,
    all_entries: bool = typer.Option(False, "--all", "-a", help="Install the whole catalog."),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
) -> None:
    """Install catalog entries into `.claude/` (agents, skills, commands, references)."""
    from engine.cli import agent_catalog

    if not names and not all_entries:
        echo("Name at least one entry or pass --all. See `dev.py agent:list`.", "red")
        raise typer.Exit(code=1)
    try:
        installed = agent_catalog.install(base_path(), None if all_entries else names, force=force)
    except (agent_catalog.UnknownCatalogEntryError, FileExistsError) as exc:
        echo(f"Install refused: {exc}. Use --force to overwrite existing files.", "red")
        raise typer.Exit(code=1) from None
    for kind, paths in installed.items():
        echo(f"  -> {kind:<10} {len(paths)} installed", "green")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

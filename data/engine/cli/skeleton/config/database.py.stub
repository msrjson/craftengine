"""Database configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

# SQLite needs no server or credentials, so a fresh checkout runs out of the
# box; Docker and production set DB_CONNECTION explicitly.
default = env("DB_CONNECTION", "sqlite")

#: Databases, besides in-memory SQLite and names ending in `_test`, that
#: `migrate fresh|reset|refresh` and `db wipe` may destroy. Comma-separated.
#: Everything else is permanent (NR-02); production is always permanent.
disposable_databases = env("DB_DISPOSABLE_DATABASES", "")

tenancy = {
    #: `warn` logs when a request proceeds with no tenant bound; `strict`
    #: raises. Default `warn` - a strict rollout is an opt-in hardening step
    #: for an app that already always binds one, not a default that could
    #: break an existing single-tenant deployment mid-upgrade.
    "guardian_mode": env("TENANCY_GUARDIAN_MODE", "warn"),
    #: Applied to every checked-out connection via `SET statement_timeout`,
    #: regardless of tenancy. `0` (PostgreSQL's own default) disables it.
    "statement_timeout_ms": env("DB_STATEMENT_TIMEOUT_MS", 0),
}

connections = {
    "sqlite": {
        "driver": "sqlite",
        "database": env("DB_DATABASE", "storage/database.sqlite"),
    },
    "pgsql": {
        "driver": "postgresql",
        "host": env("DB_HOST", "127.0.0.1"),
        "port": env("DB_PORT", 5432),
        "database": env("DB_DATABASE", "forge"),
        # Connect as a role that owns nothing, is not a superuser, and has no
        # BYPASSRLS. Row-level security does not apply to any of those, so
        # tenant isolation policies would be inert and nothing about the tables
        # would say so - `dev.py db:audit-rls` reports it, and the ScopeTenant
        # middleware refuses to serve tenant traffic under such a role.
        # Migrations run as the owning role, which is a separate credential.
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
        # `require` at minimum: `prefer` silently falls back to plaintext when
        # TLS cannot be negotiated. Set DB_SSLROOTCERT to the provider's CA and
        # DB_SSLMODE=verify-full to also pin the server identity.
        "sslmode": env("DB_SSLMODE", "require"),
        "sslrootcert": env("DB_SSLROOTCERT", ""),
        "application_name": env("APP_NAME", "craft"),
        # How many physical connections this process may hold. A thread that
        # needs one while all are checked out waits `pool_timeout` seconds and
        # then raises, rather than blocking forever. The cap is per process and
        # per connection (write and read each get their own): with a managed
        # server limit of 22 minus 3 reserved slots, budget the sum across
        # every web worker, queue worker and listener to stay under 19.
        "pool_size": env("DB_POOL_SIZE", 4),
        "pool_timeout": env("DB_POOL_TIMEOUT", 10),
        # Reopen an idle connection older than this instead of reusing it,
        # ahead of the server-side idle timeout.
        "pool_recycle": env("DB_POOL_RECYCLE", 900),
        "statement_timeout_ms": tenancy["statement_timeout_ms"],
    },
    "mysql": {
        "driver": "mysql",
        "host": env("DB_HOST", "127.0.0.1"),
        "port": env("DB_PORT", 3306),
        "database": env("DB_DATABASE", "forge"),
        "username": env("DB_USERNAME", "forge"),
        "password": env("DB_PASSWORD", ""),
    },
}

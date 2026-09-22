"""Global Framework Configurations and Features Defaults."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

FRAMEWORK_NAME = "Craft"

# Sourced from the package rather than hand-maintained here: these were literal
# strings that had already drifted from `engine/__init__.py` (claiming r00002
# against the package's r00001), so whichever one you read told you something
# different. Use `config('app.version')` / `config('app.release')`.
from craft import __release__ as FRAMEWORK_RELEASE  # noqa: E402
from craft import __version__ as FRAMEWORK_VERSION  # noqa: E402

# Global feature flags

# Off by default, and deliberately so. Multi-tenancy is an architectural
# decision with a cost - a tenant bound on every request, an isolation policy
# on every table, and a database that can actually enforce one - and it is not
# something an application should acquire by accident.
#
# The default used to be on, which made the out-of-the-box experience depend on
# the driver: a personal single-tenant app on SQLite worked only for as long as
# nobody signed in as the seeded `type = "tenant"` user, at which point the
# request was refused because SQLite cannot isolate anything. Turning it on is
# now the deliberate act, and the refusal that follows on a driver without
# isolation is then exactly right rather than a surprise.
#
# Set MULTI_TENANCY_ENABLED=true with PostgreSQL to build a tenanted product;
# see documentation/postgres.md for the two strategies and the database role
# the row-level-security one requires.
MULTI_TENANCY_ENABLED = env("MULTI_TENANCY_ENABLED", False)

# How tenants are isolated once the flag above is on.
#
#   "rls"    - shared tables, a `tenant_id` column, and a row-level security
#              policy the database enforces. Migrates once, scales to many
#              tenants, and survives a query that forgets to scope itself.
#   "schema" - one PostgreSQL schema per tenant, selected with `search_path`.
#              For the handful of tenants that need physical separation; costs
#              a migration run per tenant, on the request path.
#
# `rls` is the default because forgetting to scope a query is the failure that
# actually happens, and it is the one the database can rule out.
MULTI_TENANCY_STRATEGY = env("MULTI_TENANCY_STRATEGY", "rls")
PQC_SECURITY_ENABLED = env("PQC_SECURITY_ENABLED", True)
CAPTCHA_ENABLED = env("CAPTCHA_ENABLED", True)

# Health probes
#
# Two endpoints, because a load balancer asks two different questions.
# `/health` is liveness: it touches nothing external, so a database incident
# does not get every healthy web instance restarted on top of it. `/ready` is
# readiness: it checks the database and cache, so an instance that cannot
# serve is taken out of rotation instead of returning errors. An application
# route on either path takes precedence over the built-in one.
HEALTH_ROUTES_ENABLED = env("HEALTH_ROUTES_ENABLED", True)
HEALTH_LIVENESS_PATH = env("HEALTH_LIVENESS_PATH", "/health")
HEALTH_READINESS_PATH = env("HEALTH_READINESS_PATH", "/ready")

# How many requests one process serves at once. Zero derives it from the
# connection pool (`pool_size` x 2, at least 8), which is the right default:
# the request chain is synchronous, so a thread with no connection to borrow
# only waits out `pool_timeout` and fails. Set it explicitly for a workload
# that is mostly cached or static and rarely touches the database.
HTTP_THREADPOOL_SIZE = env("HTTP_THREADPOOL_SIZE", 0)

# Prometheus scrape endpoint. Off by default: the payload names every route
# the application serves and how often each is hit, which is reconnaissance if
# it is reachable from outside. Turn it on behind an internal network, or set
# METRICS_TOKEN and have the scraper send it as a bearer token - a request
# without it gets a 404, because an endpoint that admits it exists is an
# endpoint worth guessing at.
METRICS_ENABLED = env("METRICS_ENABLED", False)
METRICS_PATH = env("METRICS_PATH", "/metrics")
METRICS_TOKEN = env("METRICS_TOKEN", "")

# How long `dev.py migrate` waits for another instance to finish migrating
# before giving up. Every container runs migrations at boot, so without the
# lock they race; with it, the second one waits and then finds nothing pending.
MIGRATION_LOCK_TIMEOUT = env("MIGRATION_LOCK_TIMEOUT", 120)

# Default locale & timezone
DEFAULT_LOCALE = env("APP_LOCALE", "en")
SUPPORTED_LOCALES = ["en", "pt", "es"]

# Craft Engine Documentation

A batteries-included Python web framework built on Starlette.

Looking for the big picture first — what the engine contains, the build loop,
scaling from a blog to multi-tenant, and what is not implemented yet? That is
[`CRAFT_ENGINE.md`](../CRAFT_ENGINE.md).

## Getting started

| Guide | What it covers |
|---|---|
| [Introduction](introduction.md) | What Craft Engine is and how the pieces fit together |
| [Installation](installation.md) | Requirements, setup, Docker, first run |
| [Configuration](configuration.md) | `config/`, `.env`, and the `env()` helper |
| [The dev CLI](cli.md) | Every command, and the generators |
| [DX Acceleration](dx_acceleration.md) | ORM mixins (Sluggable, Publishable), fast domain development for AI & Senior Devs |
| [Market Evaluation](market_evaluation.md) | Technical assessment & positioning for AI Agents and Senior Developers |

## The essentials

| Guide | What it covers |
|---|---|
| [Service container](container.md) | Binding, resolution, autowiring, service providers |
| [Routing](routing.md) | Routes, groups, resources, route middleware |
| [Authentication](authentication.md) | Login routes, session flow, and route protection |
| [Controllers](controllers.md) | Controllers, requests, responses |
| [Views](views.md) | The Forge engine, Forge directives, layouts |
| [Validation](validation.md) | Rules, FormRequest, error handling |

## Database

| Guide | What it covers |
|---|---|
| [Migrations](migrations.md) | Schema builder, batches, rollback |
| [Database safety](database_safety.md) | Absolute data persistence, banned destructive commands, soft-delete patterns |
| [ORM](orm.md) | Models, relationships, eager loading, soft deletes |
| [Query builder](orm.md#querying--filtering) | Filtering, joins, aggregates, pagination |
| [PostgreSQL](postgres.md) | Tenant isolation with RLS, `SKIP LOCKED` queues, advisory locks, JSONB/range/full-text/vector macros, partitioning |
| [CRUD builder](crud-builder.md) | Generating a migration, model, request, resource, API and admin UI for an entity |

## Application features

| Guide | What it covers |
|---|---|
| [Security](security.md) | Authentication, authorization, WAF/firewall, honeypot, audit logs, sessions, CSRF |
| [Authorization (RBAC)](authorization.md) | Roles, permissions, the Gate fallback, `role:`/`permission:` middleware |
| [Sessions](sessions.md) | Drivers, flash data, CSRF tokens |
| [Cache](cache.md) | Stores, TTL, `remember` |
| [Queues and events](queues_events.md) | Jobs, workers, listeners |
| [API resources](resources.md) | Shaping JSON output |
| [Localization](localization.md) | BCP 47 locales, fallback chain, translations |

## Working on your app

| Guide | What it covers |
|---|---|
| [Testing](testing.md) | Running the suite, fixtures, testing against PostgreSQL |
| [Deployment](deployment.md) | Production checklist, Docker, health probes, rolling deploys, the connection budget |
| [Observability](observability.md) | Request correlation, structured logging, metrics, error reporting |

## Project resources

- [Changelog](../CHANGELOG.md)
- [Contributing](../CONTRIBUTING.md)
- [Security policy](../SECURITY.md)
- [License](../LICENSE) — MIT

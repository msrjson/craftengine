---
name: deprecation-and-migration
description: Retires old code, APIs and schema safely in Craft projects — one-release deprecated aliases for public facades and services, expand/migrate/contract for the database, never a drop in the same release. Use when removing old systems, APIs, facades, commands or features, migrating consumers to a replacement, renaming or dropping a column in production, or deciding whether to maintain or sunset existing code.
---

# Deprecation and Migration

## Overview

Code is a liability, not an asset. Every line has an ongoing cost: bugs to fix, dependencies
to update, security patches to apply, translations to maintain, and new engineers to onboard.
**Deprecation** is the discipline of removing code that no longer earns its keep;
**migration** is the process of moving consumers safely from the old to the new.

Most teams are good at building things and bad at removing them. This skill closes that gap
inside the constraints Craft imposes on every release:

- **Public API stays backward compatible across one release.** A renamed or replaced facade,
  container binding, service method, CLI command, translation key or API field keeps a
  deprecated alias for exactly one release, announced under `Deprecated` in `CHANGELOG.md`,
  and is removed in the next release under `Removed`.
- **The database only moves forward.** Schema changes use expand, migrate, contract. Nothing
  is dropped or renamed in the same release that introduces its replacement, and
  `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` and `db:drop` are never part
  of the plan.
- **Business records are never physically deleted.** Retiring data means soft deletion
  (`deleted_at`) or an `is_active` flag, not `DELETE` or `TRUNCATE`.

## When to Use

- Replacing an old service, facade, plugin, API endpoint or library with a new one
- Sunsetting a feature that is no longer needed
- Consolidating duplicate implementations (two slug sanitizers, two document validators)
- Removing dead code that nobody owns but something still depends on
- Renaming or dropping a column or table in a live database
- Renaming a translation key or a machine error `code`
- Planning the lifecycle of a new system (deprecation planning starts at design time)
- Deciding whether to keep maintaining a legacy system or invest in migrating off it

## Core Principles

### Code Is a Liability

The value of code is the capability it provides, not the code itself. When the same capability
can be delivered with less code, less complexity or a cleaner boundary, the old code should go.
In Craft that often means collapsing copies of transversal logic into one plugin under
`app/plugins/`, resolved from the container.

### Hyrum's Law Makes Removal Hard

With enough consumers, every observable behavior becomes a dependency — including bugs, timing
quirks, error codes, translation keys and the order of JSON fields. That is why deprecation
requires active migration, not an announcement. Consumers cannot "just switch" when they depend
on behavior the replacement does not reproduce.

### Deprecation Planning Starts at Design Time

When building something new, ask: "How would we remove this in three years?" Systems with
narrow interfaces resolved from the container, behavior behind feature flags, and additive
schema are cheap to retire. Systems that leak implementation details into controllers and
templates are not.

## The Deprecation Decision

Before deprecating anything, answer:

```
1. Does this still provide unique value?
   -> If yes, maintain it. If no, continue.

2. How many consumers depend on it?
   -> Quantify: call sites (grep), routes hit (logs, /metrics), tenants using it, external clients.

3. Does a replacement exist?
   -> If no, build it first. Never deprecate without an alternative.

4. What does migration cost each consumer?
   -> If it can be automated, automate it. If it is manual and heavy, weigh it against maintenance cost.

5. What does NOT deprecating cost?
   -> Security exposure, engineer time, duplicated translations and tests, complexity for newcomers.
```

## Compulsory vs Advisory Deprecation

| Type | When to use | Mechanism |
|---|---|---|
| **Advisory** | Migration is optional and the old path is stable | `DeprecationWarning`, changelog entry, documentation. Consumers migrate on their own schedule. |
| **Compulsory** | The old path has a security issue, blocks progress, or is too costly to keep | Removal in a named release. Migration tooling and guide provided. |

**Default to advisory — but for public framework and application API, the window is fixed:**
the alias lives for exactly one release and is removed in the next. Anything longer needs an
explicit decision recorded in an ADR. Compulsory deprecation still requires tooling,
documentation and support; announcing a deadline is not a migration plan.

## The Migration Process

### Step 1: Build the Replacement

Never deprecate without a working alternative. The replacement must:

- Cover every critical use case of the old path
- Have documentation and a migration guide
- Be proven in production (behind a flag if needed), not just "theoretically better"
- Pass the same gates: pytest, ruff, `lint_language.py`, `lint_structure.py`

### Step 2: Announce and Document

The announcement lives in the same change that introduces the deprecated alias, as a
`Deprecated` entry under `## [Unreleased]`:

```markdown
## [Unreleased]

### Deprecated

- `InvoiceService.generate_boleto()` is deprecated in favor of
  `BankSlipService.generate_bank_slip()` and will be removed in the next release.
  The old method delegates to the new one and emits `DeprecationWarning`.
  Migration: replace the call and resolve `BankSlipService` from the container;
  the returned object is identical. Search with `grep -rn "generate_boleto" app/ tests/`.
```

For larger deprecations, add a guide under the project documentation:

```markdown
## Deprecation Notice: LegacyTaskService

**Status:** Deprecated in 3.21.0 (r00014)
**Replacement:** TaskService (see migration guide below)
**Removal:** next release
**Reason:** LegacyTaskService issues raw SQL from the service layer and cannot be
            scoped per tenant. TaskService delegates to TaskRepository and is tenant-scoped.

### Migration Guide
1. Resolve `TaskService` from the container instead of `LegacyTaskService`.
2. Replace `find(task_id)` with `find_for_user(task_id, user)`; it enforces the policy check.
3. Run `python -m pytest tests -W error::DeprecationWarning` to prove no call site remains.
```

### Step 3: Migrate Incrementally

Migrate consumers one at a time, not all at once. For each consumer:

```
1. Identify every touchpoint with the deprecated path (grep, route logs, container resolutions)
2. Switch it to the replacement
3. Verify behavior matches (tests, feature tests, integration checks on PostgreSQL)
4. Remove its references to the old path
5. Confirm no regressions, then commit — one consumer, one commit
```

**The Churn Rule.** If you own what is being deprecated, you are responsible for migrating its
consumers — or for providing a backward-compatible alias that needs no migration. Announcing a
deprecation and leaving consumers to work it out is not deprecation, it is breakage on a delay.

### Step 4: Remove the Old Path

Only in the release after the deprecation, and only after every consumer has migrated:

```
1. Verify zero active use: grep shows no call sites, logs show no hits on old routes,
   the suite passes with `-W error::DeprecationWarning`
2. Remove the alias or old code
3. Remove its tests, documentation, configuration and translation keys
   (translation rows are retired through a forward migration or seeder change, never by hand)
4. Add a `Removed` entry under `## [Unreleased]` naming the replacement
5. Cut the release with a major bump if external consumers could still observe the removal
6. Celebrate — removing code is an achievement
```

## Migration Patterns

### Deprecated Alias for One Release (public API)

Every public name that changes keeps its old name working for one release. The alias delegates
to the new implementation and warns — it never duplicates logic.

**A service method:**

```python
"""Invoice service with a deprecated method kept for one release."""

import warnings


class InvoiceService:
    """Business logic for invoices."""

    def __init__(self, bank_slips: "BankSlipService") -> None:
        """Receive collaborators from the container.

        Args:
            bank_slips: Service that issues bank slips.
        """
        self._bank_slips = bank_slips

    def generate_boleto(self, invoice_id: int) -> "BankSlip":
        """Deprecated alias of `BankSlipService.generate_bank_slip`.

        Deprecated in 3.21.0; removed in the next release.

        Args:
            invoice_id: Invoice to issue the bank slip for.

        Returns:
            The generated bank slip.
        """
        warnings.warn(
            "InvoiceService.generate_boleto() is deprecated; "
            "use BankSlipService.generate_bank_slip()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._bank_slips.generate_bank_slip(invoice_id)
```

The warning text is a developer diagnostic in English, not user-facing copy, so it is not a
translation key. It must never reach a rendered page or an API response.

**A container binding:** when a binding key changes, register the old key as an alias of the
new one in the service provider so `make("old_key")` keeps resolving for one release:

```python
app.singleton("bank_slips", lambda container: BankSlipService(container.make("db")))
# Deprecated in 3.21.0, removed in the next release: resolve "bank_slips" instead.
app.alias("bank_slips", "boletos")
```

Check the service provider's registration hook in the project before copying; the container's
`alias(abstract, alias)` makes the second name resolve to the first.

**A facade:** the core facade accessors (`db`, `router`, `view`, `auth`, `cache`, `antispam`,
`firewall`, `honeypot`, ...) are pinned by `tests/test_release_non_regression.py`. Never change
one in place. If an application facade must be renamed, keep the old name importable for one
release through a module-level `__getattr__` (PEP 562), which fires only for names the module
does not define — so the old name warns on import while the new one stays silent:

```python
"""Application facades. `SpamGuard` is a deprecated name kept for one release."""

import warnings

from craft.facades import AntiSpam

__all__ = ["AntiSpam"]

_DEPRECATED_NAMES: dict[str, tuple[type, str]] = {
    "SpamGuard": (AntiSpam, "AntiSpam"),
}


def __getattr__(name: str) -> type:
    """Resolve a deprecated facade name to its replacement, with a warning.

    Args:
        name: Attribute requested from this module.

    Returns:
        The replacement facade class.

    Raises:
        AttributeError: When the name is neither defined nor deprecated.
    """
    if name not in _DEPRECATED_NAMES:
        raise AttributeError(name)
    replacement, replacement_name = _DEPRECATED_NAMES[name]
    warnings.warn(
        f"{name} is deprecated; use {replacement_name}",
        DeprecationWarning,
        stacklevel=2,
    )
    return replacement
```

Add a test that the old name resolves to the same facade (same `get_facade_accessor()`) and
emits `DeprecationWarning` under `pytest.warns`, and delete that test together with the alias.

**A CLI command, route, API field, error code or translation key:** the same rule applies. Keep
the old command name registered as a wrapper that warns; keep the old route answering (or
redirecting) for one release; return both the old and new API field for one release; accept
both error codes in clients; keep the old translation key's `en`, `pt-BR` and `es` rows until
the release that removes it.

### Strangler Pattern

Run the old and new implementations side by side and move traffic gradually. When the old one
handles nothing, remove it.

```
Phase 1: new handles 0%, old handles 100%
Phase 2: new handles 10% (canary: one pilot tenant or a percentage of users)
Phase 3: new handles 50%
Phase 4: new handles 100%, old idle
Phase 5: remove old (next release, `Removed` changelog entry)
```

### Adapter Pattern

An adapter translates calls from the old interface to the new implementation. Consumers keep
the old interface while the backend is replaced underneath.

```python
"""Adapter exposing the legacy task interface over the new service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LegacyTask:
    """Shape returned by the deprecated interface."""

    id: int
    title: str
    is_done: bool


class LegacyTaskAdapter:
    """Old method signatures, delegating to `TaskService`."""

    def __init__(self, tasks: "TaskService") -> None:
        """Receive the new service from the container.

        Args:
            tasks: The replacement task service.
        """
        self._tasks = tasks

    def get_task(self, task_id: int) -> LegacyTask:
        """Return a task in the legacy shape.

        Args:
            task_id: Identifier of the task.

        Returns:
            The task converted to the legacy dataclass.
        """
        task = self._tasks.find(task_id)
        return LegacyTask(id=task.id, title=task.title, is_done=task.completed_at is not None)
```

### Feature Flag Migration

Switch consumers from old to new one at a time, deciding in one place:

```python
def resolve_task_service(app: "Application", tenant_id: int) -> "TaskReader":
    """Pick the task implementation for a tenant during the migration window.

    Args:
        app: The application container.
        tenant_id: Tenant being served.

    Returns:
        The new service when the flag is on for the tenant, otherwise the adapter.
    """
    flags = app.make("feature_flags")
    if flags.is_enabled("tasks.new_service", tenant_id=tenant_id):
        return app.make("tasks")
    return app.make("legacy_tasks")
```

The `feature_flags` binding is project-owned (see the `ci-cd-and-automation` skill,
`.claude/skills/ci-cd-and-automation/SKILL.md`). A flag decides which code runs; it never
decides whether a migration runs.

### Database Schema Migrations — Expand, Migrate, Contract

A schema change is the riskiest migration because data is the one thing a redeploy cannot
restore. In Craft it is doubly so: migrations are forward-only, and the rollback plan for any
release is to redeploy the **previous application version against the new schema**. The failure
mode is coupling the schema change to the code change — rename a column in the same release that
starts reading the new name, and during rollout (or after a rollback) one version queries a
column that does not exist.

The rule: **never change a column in place, and never drop in the same release that adds.**
Move in additive phases so the old and the new code are both valid at every step.

```
EXPAND ───────────────────> MIGRATE ────────────────────> CONTRACT
add the new column,         dual-write old + new,          once no released code reads
nullable, alongside         backfill in batches,           the old column, stop writing it,
the old one                 switch reads to the new one    then drop it in a LATER release
```

**Worked example — renaming `users.name` to `users.full_name`:**

1. **Expand (release N).** Add `full_name` as nullable. Old code ignores it; nothing breaks.

   ```python
   """Migration: add users.full_name alongside users.name."""

   from craft.migrations import Schema


   def up() -> None:
       """Add the new nullable column; the old column stays untouched."""
       Schema.table("users", lambda t: (t.string("full_name").nullable(),))


   def down() -> None:
       """Development-only reversal; production never rolls back migrations."""
       Schema.drop_column("users", "full_name")
   ```

   The `down()` exists so the migration can be exercised locally and in tests; in shared
   environments the path is always forward. Generate the file with
   `python dev.py make:migration add_full_name_to_users`.

2. **Dual-write (release N).** The model or repository writes both `name` and `full_name` on
   every insert and update. Old code keeps working; new rows are complete.

3. **Backfill (release N, after deploy).** Copy `name` into `full_name` for existing rows, in
   batches, off the request path — a queued job or a scheduled task, with the SQL in a
   repository:

   ```python
   """Repository method that backfills users.full_name in bounded batches."""

   from craft.facades import DB


   class UserBackfillRepository:
       """Raw SQL for the full_name backfill."""

       BATCH_SIZE = 500

       def backfill_full_name_batch(self) -> int:
           """Copy `name` into `full_name` for one batch of rows.

           Returns:
               Number of rows updated; zero means the backfill is complete.
           """
           ids = [
               row["id"]
               for row in DB.select(
                   "SELECT id FROM users WHERE full_name IS NULL ORDER BY id LIMIT ?",
                   [self.BATCH_SIZE],
               )
           ]
           if not ids:
               return 0
           placeholders = ", ".join("?" for _ in ids)
           return DB.update(
               f"UPDATE users SET full_name = name WHERE id IN ({placeholders})", ids
           )
   ```

   The job calls the method until it returns zero, pausing between batches. It is idempotent
   and resumable: re-running it only touches rows still missing the value.

4. **Switch reads (release N+1).** Point the application at `full_name`, keep writing both.
   Deploy and let it bake. If this release misbehaves, redeploying release N is safe:
   `name` is still written and read there.

5. **Contract (release N+2, alone).** Stop writing `name` in one release. Only after that
   release has run in production — and the previous release it would roll back to no longer
   reads `name` — drop the column in its own migration, with a `Removed` changelog entry.

Each step deploys independently, and at every step the previous release still runs against the
schema. Treat each phase as a thin vertical slice (the `incremental-implementation` skill,
`.claude/skills/incremental-implementation/SKILL.md`).

**Rules:**

- **Additive first; destructive last, alone, and later.** New nullable columns, new tables and new
  indexes are safe in any release. Drops and renames get their own release, after no released
  code references the old shape.
- **Never drop in the same release that adds.** The previous release is the rollback target, and
  it still needs the old shape.
- **Forward-only in every shared environment.** Never plan on `migrate:rollback` in production,
  and never use `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop`
  anywhere. A correction is a new forward migration.
- **Backfill in batches, off the hot path.** A single `UPDATE` over millions of rows locks the
  table. Chunk, throttle, make it resumable.
- **Build large indexes without blocking writes.** On PostgreSQL use
  `CREATE INDEX CONCURRENTLY` through `Schema.raw(...)`, and confirm first whether the migrator
  wraps the migration in a transaction — `CONCURRENTLY` cannot run inside one.
- **Retire data, do not delete it.** Business rows are soft-deleted (`t.soft_deletes()` in the
  schema, the `SoftDeletes` mixin on the model); tables are dropped only after their data is
  archived and no release reads them.
- **Personal data follows its retention policy.** Dropping a column that held personal data is
  itself an LGPD/GDPR decision: document the retention basis, and anonymize or export before the
  contract step if required.
- **Decouple risky cutovers with a flag**, exactly as in the Feature Flag Migration pattern above.

## Zombie Code

Zombie code is code nobody owns but something still depends on. It is not maintained, has no
clear owner, and accumulates vulnerabilities and incompatibilities. Signs:

- No commits in six months or more, yet active call sites or route hits
- No assigned maintainer
- Tests skipped or failing that nobody fixes
- Dependencies with known vulnerabilities (`pip-audit`) that nobody updates
- Translation keys referenced nowhere, or references to keys that no longer exist
- Documentation describing modules or commands that are gone

**Response:** assign an owner and maintain it properly, or deprecate it with a concrete migration
plan. Zombie code cannot stay in limbo — it gets investment or it gets removed.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It still works, why remove it?" | Unmaintained working code accumulates security debt and complexity. The cost grows silently. |
| "Someone might need it later" | If it is needed later it can be rebuilt. Keeping it "just in case" costs more. |
| "The migration is too expensive" | Compare it with two to three years of maintaining both. Migration is usually cheaper. |
| "We'll deprecate it after the new system is done" | Plan deprecation at design time. By then there will be new priorities. |
| "Consumers will migrate on their own" | They will not. Provide tooling and documentation, or migrate them yourself (the Churn Rule). |
| "We can maintain both indefinitely" | Two implementations double the tests, translations, documentation and onboarding. |
| "Just rename the method, it's one line" | Public API keeps a deprecated alias for one release. Every consumer you cannot see breaks otherwise. |
| "Just rename the column, it's one line" | Old and new code run together during rollout and after a rollback. Expand/contract, never rename in place. |
| "Add the new column and drop the old one in the same migration" | The previous release — your rollback target — still reads the old column. Drop it in a later release. |
| "We'll roll the migration back if it goes wrong" | Migrations are forward-only. Make every step additive so the previous release still runs. |
| "It's a test database, migrate:fresh is fine" | Those commands are banned in every environment, and using them hides migrations that cannot run forward. |
| "Delete the old rows, nobody reads them" | Business records are soft-deleted. Physical deletes destroy audit history and may violate retention duties. |

## Red Flags

- A deprecated path with no working replacement
- A deprecation with no `Deprecated` changelog entry, migration guide or tooling
- A public facade accessor, container key, command, API field, error code or translation key
  changed or removed without a one-release alias
- An alias that outlived its one release with no recorded decision
- "Soft" deprecations advisory for years with no progress
- Zombie code with no owner and active consumers
- New features added to a deprecated path instead of the replacement
- Removal without measuring current use (grep, logs, `-W error::DeprecationWarning`)
- A schema change and the code that depends on it shipped in the same release
- A column renamed or dropped in place instead of through expand/migrate/contract
- A drop in the same release that adds the replacement
- A plan that relies on `migrate:rollback`, `migrate:reset`, `migrate:fresh`, `db:wipe` or `db:drop`
- A backfill as one unbounded `UPDATE`, or run on the request path
- `DELETE` or `TRUNCATE` on business entities

## Verification

After deprecating public API:

- [ ] The replacement is production-proven and covers every critical use case
- [ ] The old name is a delegating alias that emits `DeprecationWarning`, with a test for it
- [ ] `CHANGELOG.md` has a `Deprecated` entry naming the replacement and the removal release
- [ ] A migration guide exists with concrete steps
- [ ] `tests/test_release_non_regression.py` still passes

After removing the deprecated path (next release):

- [ ] Zero remaining consumers, verified by grep, logs and `python -m pytest tests -W error::DeprecationWarning`
- [ ] Old code, its tests, documentation, configuration and translation keys are removed
- [ ] `CHANGELOG.md` has a `Removed` entry; the version bump reflects what consumers can observe
- [ ] No references to the deprecated path remain in the codebase
- [ ] Gates pass: pytest, ruff, `lint_language.py`, `lint_structure.py`

After a database schema migration:

- [ ] The change ships in additive phases (expand -> dual-write and backfill -> switch reads -> contract), never in place
- [ ] At every release, the previous release still runs against the schema
- [ ] No drop or rename ships in the same release as its replacement; the contract step ships alone, later
- [ ] Migrations are forward-only; no banned destructive command appears anywhere
- [ ] Backfills are batched, throttled, idempotent and off the request path
- [ ] Business data is soft-deleted, and personal data removal follows the documented retention policy

# Craft Engine - Critical Database Safety & Data Persistence Rule

Target Framework: Craft Engine (Python / dev.py CLI)
Core Principle: ABSOLUTE DATA PERSISTENCE. Never wipe, drop, truncate, or reset database state under any circumstances, across any environment (development, test, demo, staging, or production).

## 1. BANNED CRAFT ENGINE CLI COMMANDS
You are STRICTLY FORBIDDEN from suggesting, outputting, or executing any destructive `dev.py` commands, including:
- `python dev.py migrate:reset`
- `python dev.py migrate:refresh`
- `python dev.py migrate:fresh`
- `python dev.py db:wipe`
- `python dev.py db:drop`
- `python dev.py db:seed --fresh` (or any flag that clears tables prior to seeding)
- Destructive container commands affecting database mounts (e.g., `docker compose down -v`, `docker volume rm`).

## 2. EXECUTION & CODE MODIFICATION RULES
- Database evolution must be forward-only using incremental migrations (`python dev.py migrate`).
- Never perform raw SQL queries or ORM calls containing physical `DELETE`, `TRUNCATE`, or `DROP TABLE/DATABASE/VIEW`.
- Enforce Soft-Delete patterns exclusively for record removals (e.g., mutating flags or timestamps like `deleted_at = now()`, `is_active = False` via `UPDATE`).
- The Demo tenant is considered permanent reference data: never treat Demo environments as disposable or clearable for testing.

## 3. ABORT CONDITION
If a requested task implies dropping tables, purging test data, or resetting schema state, REFUSE the destructive action immediately and provide an additive, non-destructive migration alternative.

## 4. WORKSPACE INSPECTION & DISCOVERY (ZERO GUESSING)
- NEVER guess credentials, paths, configurations, or subsystem states.
- Always inspect and read the workspace first before taking action (e.g. check `.github/api-key` for repository credentials, check workspace directory layout, inspect existing config files and environment variables).
- Ground every action in concrete files discovered within the workspace, avoiding unverified assumptions or guesses.

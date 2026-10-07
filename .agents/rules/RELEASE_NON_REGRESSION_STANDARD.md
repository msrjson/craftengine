# RELEASE NON-REGRESSION STANDARD & GOVERNANCE
Target: Craft Engine Framework (`msrjson/craftengine`) & Ecosystem Applications

This standard defines the non-negotiable contract to prevent regressions across releases, guaranteeing absolute database persistence, backward compatibility, type safety, and security.

---

## 1. THE SEVEN NON-REGRESSION LAWS (NR-01 to NR-07)

### NR-01 — Strict Version Synchronization & Monotonic Release Counter
1. **Single Source of Truth**: The application version and release counter MUST be synchronized across:
   - `data/pyproject.toml` (`[project].version`)
   - `data/engine/__init__.py` (`__version__`, `__release__`)
   - `data/CHANGELOG.md` (`## [X.Y.Z] rNNNNN — YYYY-MM-DD`)
2. **Monotonic Counter**: The release counter `__release__ = "rNNNNN"` increments by exactly `+1` on every cut release (e.g. `r00011` -> `r00012`). It is never reset, never skipped, and never decremented, regardless of whether the semantic version bump is Major, Minor, or Patch.
3. **Release Tagging**: Git tags must strictly match `vMAJOR.MINOR.PATCH-rNNNNN`.

### NR-02 — Absolute Database Safety & Data Persistence
1. **Zero Destructive Operations**: `migrate:reset`, `migrate:refresh`, `migrate:fresh`, `db:wipe`, `db:drop`, and `db:seed --fresh` are permanently banned in all environments (development, test, demo, staging, and production).
2. **Forward-Only Migrations**: Database evolution is exclusively forward-moving through incremental schema operations.
3. **Soft-Deletes Exclusively**: Physical `DELETE` or `TRUNCATE` queries on business entities are forbidden. Record deactivation must mutate flags or timestamps (`deleted_at`, `is_active = False`).
4. **Demo Tenant Immobility**: The seeded demo tenant is permanent reference data and must never be purged or reset during release testing.

### NR-03 — Mandatory Pre-Release Automated Verification Gate
Before cutting or publishing any release, the verification pipeline MUST pass with zero errors:
1. **Unit & Integration Tests**: `python -m pytest tests` must execute with 100% pass rate.
2. **Linter Gate**: `ruff check engine` must execute with zero lint or structural violations.
3. **Language Standard Gate**: `python .agents/rules/lint_language.py --config language-standard.toml` must pass clean.
4. **Non-Regression Verification**: `tests/test_release_non_regression.py` must pass, validating version synchronization, facade integrity, and database safety invariants.

### NR-04 — Immutable Changelog & Traceability Contract
1. **Atomic Documentation**: Every code modification (bug fix, new feature, security patch, dependency change) MUST add its entry under `## [Unreleased]` in `CHANGELOG.md` within the same commit.
2. **Release Promotion**: When cutting a release, `## [Unreleased]` is renamed to `## [X.Y.Z] rNNNNN — YYYY-MM-DD`, and a fresh, empty `## [Unreleased]` section is opened immediately above it.
3. **Categorized Entries**: Changes must be categorized using standard Keep a Changelog taxonomy: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

### NR-05 — Public API & Facade Backward Compatibility
1. **No Silent Signature Breaks**: Public facades in `craft.facades` (`Auth`, `DB`, `Route`, `View`, `Cache`, `Firewall`, `Honeypot`, `AntiSpam`, `Image`, etc.) must remain backward-compatible.
2. **Container Binding Stability**: Core singleton keys registered in `Application` container (`db`, `router`, `view`, `auth`, `antispam`, `firewall`, etc.) must preserve their public methods.
3. **Facade Swapping Invariant**: `Facade._swap(double)` and `Facade._clear_resolved()` must function reliably across all facades for isolated testing.

### NR-06 — Form Validation & Anti-Spam Security Standard
1. **CSRF Enforcement**: Every state-altering HTTP form (`POST`, `PUT`, `PATCH`, `DELETE`) rendered by Forge must include `@csrf`.
2. **Spam & Bot Defense**: Public forms exposed to internet traffic must implement anti-spam protection via `@honeypot` / `@antispam` or `FormRequest` anti-spam validation.
3. **Constant-Time Verification**: All security tokens, honeypot timestamps, signatures, and captcha challenges must compare digests using `hmac.compare_digest` to prevent timing-attack side channels.
4. **Resilient Audit Trail**: If a honeypot or spam trap is triggered, the event must be recorded in `security_events` table without crashing or interrupting the security response lifecycle.

### NR-07 — Pure Python 3.14+ Modern Architecture
1. **Pure Python Backend**: Craft Engine is 100% Python 3.14+; zero Node.js, Webpack, or TypeScript build toolchains.
2. **Type Safety**: New modules and classes must declare explicit Python typing annotations and utilize modern language features (e.g. `Self`, modern union types `X | Y`, type aliases).
3. **Async / Sync Dual-Path Safety**: Async actions in HTTP kernel must not block event loop threads; database pool access in worker threads must properly release pooled connections.

---

## 2. PRE-RELEASE AUDIT CHECKLIST

Agents and maintainers must verify each check prior to tagging a release:

- [ ] `pyproject.toml` version matches `engine/__init__.py` `__version__`.
- [ ] `engine/__init__.py` `__release__` is exactly previous release + 1.
- [ ] `CHANGELOG.md` has `## [X.Y.Z] rNNNNN — YYYY-MM-DD` and a fresh `## [Unreleased]`.
- [ ] `ruff check engine` outputs `All checks passed!`.
- [ ] `python -m pytest tests` outputs all passed with zero failures.
- [ ] `python .agents/rules/lint_language.py --config language-standard.toml` outputs `Language standard: clean.`.
- [ ] No raw destructive SQL commands or drop table statements in code.

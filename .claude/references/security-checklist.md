# Security Checklist

Quick reference for Craft Engine application security. Use alongside the
`security-and-hardening` skill (`.claude/skills/security-and-hardening/SKILL.md`).

## Table of Contents

- [Threat Modeling (Start Here)](#threat-modeling-start-here)
- [Pre-Commit Checks](#pre-commit-checks)
- [Authentication](#authentication)
- [Authorization](#authorization)
- [Input Validation](#input-validation)
- [Forms, CSRF and Anti-Spam](#forms-csrf-and-anti-spam)
- [Security Headers](#security-headers)
- [Cross-Origin Access](#cross-origin-access)
- [Data Protection](#data-protection)
- [Audit Trail](#audit-trail)
- [Dependency Security](#dependency-security)
- [AI / LLM Security](#ai--llm-security)
- [Error Handling](#error-handling)
- [OWASP Top 10 Quick Reference](#owasp-top-10-quick-reference)
- [OWASP Top 10 for LLMs Quick Reference](#owasp-top-10-for-llms-quick-reference)

## Threat Modeling (Start Here)

Before reaching for controls, spend five minutes thinking like an attacker:

- [ ] Trust boundaries mapped (requests, uploads, webhooks, third-party APIs, queue payloads, LLM output, and local values written by processes you do not control)
- [ ] Assets named (credentials, `APP_KEY`, personal data, payment data, admin actions, tenant isolation, money movement)
- [ ] STRIDE run per boundary (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege)
- [ ] Abuse cases written next to use cases ("how would I misuse this?"), each one a `pytest` case

## Pre-Commit Checks

- [ ] No secrets in code (`git diff --cached | grep -iE "password|secret|api_key|token|app_key"`)
- [ ] `.gitignore` covers `.env`, `.env.*.local`, `*.pem`, `*.key`, `storage/logs/`, `storage/framework/sessions/`
- [ ] `.env.example` uses placeholder values, never real secrets
- [ ] Gates green: `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py`, `python .claude/rules/lint_structure.py`

## Authentication

- [ ] Passwords hashed with `Hash.make()` (bcrypt, with a PBKDF2-HMAC-SHA256 fallback) and verified with `Hash.check()`
- [ ] `Hash.needs_rehash()` checked after a successful login, and the hash upgraded
- [ ] Users signed in through `Auth.login()` / `Auth.attempt()`, which regenerate the session id (no session fixation)
- [ ] Session cookie: `httponly` (always set by `StartSession`), `SESSION_SECURE_COOKIE=true`, `SESSION_SAME_SITE=lax` or `strict`
- [ ] `SESSION_LIFETIME` set to a reasonable value; `SESSION_DRIVER=file` when the payload should not travel in the cookie
- [ ] A real `APP_KEY` generated with `python dev.py key:generate`; never the ephemeral development key in production
- [ ] `throttle` middleware on login, registration and password-reset routes (default 10 attempts per 60 seconds per IP and path)
- [ ] Throttle counters in a shared cache driver when more than one worker or instance serves traffic
- [ ] Password reset tokens: time-limited (1 hour or less), single-use, stored hashed
- [ ] Login failures do not reveal whether the account exists
- [ ] Account lockout or cooldown after repeated failures (the `Honeypot` service keeps `auth_cooldowns`), with notification
- [ ] MFA supported for sensitive operations (optional but recommended)

## Authorization

- [ ] Every protected route carries `auth` (session) or `api` (bearer token) middleware
- [ ] Role and permission routes use `role:<slug>`, `permission:<slug>` or `group:<slug>`
- [ ] Every action on a record checks ownership through `Gate.authorize()` or a registered Policy (prevents IDOR)
- [ ] Policies registered in `app/Providers/AuthServiceProvider.py` with `Gate.policy(Model, Policy)`
- [ ] No reliance on "the Gate will allow it": the Gate denies unknown abilities by default, and tests assert the 403
- [ ] Admin actions check the role inside the action as well as on the route
- [ ] Tenant-scoped data isolated at the query layer (`ScopeTenant` / row-level security or schema strategy)
- [ ] API tokens scoped to the minimum permissions and stored as SHA-256 digests
- [ ] Signed tokens (if used) validated for signature, expiry, issuer and audience

## Input Validation

- [ ] All input validated at the boundary with a `FormRequest` (`app/Http/Requests`) or `Validator`
- [ ] Only `validated()` output reaches `create()` / `update()`; models declare `fillable`, never `guarded = False`
- [ ] Validation uses allowlists (`in:`, `regex:`), not denylists
- [ ] String lengths constrained (`min:`, `max:`)
- [ ] Numeric ranges validated (`between:`, `integer`, `numeric`)
- [ ] E-mail, URL, date, UUID and IP formats validated with the matching rules
- [ ] Markup refused where it has no place (`no_html`)
- [ ] File uploads: `file` / `image`, `mimes:`, `max_file_size:` in kilobytes, magic bytes checked for critical paths, stored name generated server-side
- [ ] No SQL built by string formatting; SQL only in repositories, values passed as bindings
- [ ] HTML output escaped by Forge; no `| safe` on user content; no `innerHTML` with user content in static `.js`
- [ ] Redirect targets validated against an allowlist (prevents open redirect)
- [ ] Server-side URL fetches allowlisted; private and reserved addresses rejected (prevents SSRF)
- [ ] No `eval`, `exec`, `pickle.loads` or unsafe YAML loading on untrusted data; `subprocess` with argument lists, never `shell=True`
- [ ] Destructive path operations (delete, move, overwrite): symlinks resolved, allowlisted root, minimum depth, ownership evidence read before the call

### Destructive Path Operations

Containment for a target named by data. Resolve first, then decide — and treat the result as
a candidate, not as authorization:

```python
from pathlib import Path

ALLOWED_ROOTS: tuple[Path, ...] = (Path("/var/lib/craft-app/exports").resolve(),)  # an allowlist, not a pattern
MIN_DEPTH = 1                                                                   # so a root is never the target
OWNER_MARKER = ".owner"


def resolve_deletable(candidate: str, expected_owner: str) -> Path:
    """Resolve a deletion target and prove it is contained and owned.

    Args:
        candidate: The path named by a payload, a config value or another process.
        expected_owner: The owner id taken from authenticated state, never from the payload.

    Returns:
        The resolved target, as a candidate for deletion.

    Raises:
        UnsafeDeletionTargetError: When the target is outside the roots, is a root, or is not proven ours.
    """
    target = Path(candidate).resolve(strict=True)  # symlinks resolved BEFORE the check
    root = next((r for r in ALLOWED_ROOTS if target.is_relative_to(r)), None)
    if root is None or len(target.relative_to(root).parts) < MIN_DEPTH:
        raise UnsafeDeletionTargetError(code="DELETE_TARGET_OUTSIDE_ROOTS", target=str(target))

    marker = target / OWNER_MARKER
    owner = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
    if owner != expected_owner:
        raise UnsafeDeletionTargetError(code="DELETE_TARGET_UNPROVEN_OWNER", target=str(target))
    return target
```

`Path.is_relative_to` compares path components, so a sibling such as `exports-old` does not
pass as a child of `exports`, while a legitimate child named `..cache` is not mistaken for a
parent reference. Log every refusal with the rejected target, and stop — never fall back to a
broader default path.

What this does not do, and must be said wherever the snippet is copied:

- **The marker is self-attestation.** Anything that can write inside the root can write
  `.owner`. `expected_owner` has to come from authenticated state, and the marker needs
  integrity protection (restrictive ownership, or an HMAC keyed with a secret the writer does
  not hold, verified with `hmac.compare_digest`) before it is authorization rather than a
  consistency check against a misderived target.
- **Returning a path leaves a check/use race.** Where an untrusted process can swap an ancestor
  between the check and the call, operate on a descriptor (`os.open(..., os.O_NOFOLLOW)`,
  `dir_fd=` arguments to `os.unlink` / `os.rmdir`), or guarantee the hierarchy is immutable for
  the duration.

## Forms, CSRF and Anti-Spam

- [ ] `VerifyCsrfToken` in the global middleware stack, after `StartSession` (it raises without a session)
- [ ] `SESSION_CSRF=true`; disabled only for a purely stateless API
- [ ] Every state-changing form (`POST`, `PUT`, `PATCH`, `DELETE`) rendered by Forge contains `@csrf`
- [ ] JavaScript requests send the token in `X-CSRF-Token`; tokens are never accepted from the query string
- [ ] The exempt list (`api/*` by default) contains only routes protected by the `api` bearer-token middleware
- [ ] Every public form contains `@honeypot` or `@antispam`, and its `FormRequest` sets `antispam = True` (or calls `AntiSpam.validate()`)
- [ ] Tokens, signatures, honeypot timestamps and captcha answers compared with `hmac.compare_digest`
- [ ] Spam and honeypot detections recorded in `security_events` without interrupting the response

## Security Headers

`SecurityHeaders` sets the first group on every response. CSP and HSTS are sent **only when
configured** as `security.csp` / `security.hsts` (for example in `config/security.py`).
Headers are applied "if absent", so a response that already carries one keeps its value.

```text
X-Content-Type-Options: nosniff                          (always)
X-Frame-Options: DENY                                    (always)
Referrer-Policy: strict-origin-when-cross-origin         (always)
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

`SecurityHeaders` also sends `X-XSS-Protection: 1; mode=block`. Current guidance is `0`
(the legacy filter is disabled and CSP does the work); set it explicitly on the response if
your audit requires it. Keep scripts in vendored static files so the CSP needs no
`'unsafe-inline'`.

## Cross-Origin Access

```python
# Restrictive (recommended): an explicit allowlist, checked per request
ALLOWED_ORIGINS: frozenset[str] = frozenset({"https://example.com", "https://app.example.com"})
ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE"
ALLOWED_HEADERS = "Content-Type, Authorization, X-CSRF-Token"


def cross_origin_headers(origin: str | None) -> dict[str, str]:
    """Return the cross-origin headers for an allowed origin, or none at all.

    Args:
        origin: The request's `Origin` header.

    Returns:
        The headers to add to the response.
    """
    if origin not in ALLOWED_ORIGINS:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Allow-Headers": ALLOWED_HEADERS,
        "Vary": "Origin",
    }

# NEVER in production:
#   "Access-Control-Allow-Origin": "*"      together with credentials
#   "Access-Control-Allow-Origin": origin   reflected without the allowlist check
```

Register it as a middleware (`make:middleware`, then `kernel.alias_middleware(...)`), keep the
origin list in configuration, and answer preflight `OPTIONS` requests from the same function.

## Data Protection

- [ ] Sensitive attributes listed in the model's `hidden` (`password`, `api_token`, `remember_token`)
- [ ] APIs return Resources (`make:resource`) with explicit fields, not raw models
- [ ] Sensitive data never logged (passwords, tokens, session ids, full card numbers, full `CPF`)
- [ ] Personal data encrypted at rest where regulation or classification requires it
- [ ] HTTPS for all external communication; `SESSION_SECURE_COOKIE=true`
- [ ] Database backups encrypted, with access restricted and restores tested
- [ ] Personal data classified, collected against a stated purpose, with a retention period
- [ ] Erasure requests anonymize personal fields on soft-deleted rows (soft delete alone is not erasure), including caches, search indexes and backups on their rotation
- [ ] Export (access) requests produce the person's data in a machine-readable format
- [ ] Consent recorded before collection or third-party sharing; vendors have a data-processing agreement

## Audit Trail

- [ ] Firewall threats, spam traps and honeypot hits land in `security_events`; login attempts in `auth_audit_logs`
- [ ] Audit writes never crash the request they are recording
- [ ] Reviewed routinely with `python dev.py security:audit` and `python dev.py firewall:list`
- [ ] IP blocks and allowances changed through `python dev.py firewall:block` / `firewall:allow`, with a reason
- [ ] `FirewallMiddleware` enabled only behind a proxy that overwrites `X-Forwarded-For` (it trusts the first entry)
- [ ] Security-relevant actions (role grants, permission changes, exports, erasures) logged with actor id, target id and `request_id`, never with the personal data itself

## Dependency Security

Craft is pure Python: dependencies are declared in `pyproject.toml` and the frontend is
vendored static `.js` and `.css`. There is no JavaScript package manager and no Node build
step — adding one adds a supply chain and breaks the stack boundary.

First locate the **installation boundary**: the project root that owns `pyproject.toml` and
the committed pinned dependency set. CI installs from exactly that set. Stop if two competing
pin files exist at one root, or if CI installs something different from what is committed.

| Concern | Command |
|---|---|
| Reproducible install | `pip install --require-hashes -r <pinned requirements file>` |
| Avoid install-time code execution | `pip install --only-binary :all: ...` where every dependency ships wheels |
| Known-advisory audit | `pip-audit` against the pinned set (or the project's equivalent auditor) |
| Tests against the upgrade | `python -m pytest tests` |
| Lint after the upgrade | `ruff check engine` |

For another installer, use its own documented frozen-install and audit commands; do not
substitute commands from a different tool.

### Install-Time Code Gate

A source distribution executes its build backend on install. Treat that as running the
package's code on your machine.

1. Prefer wheels; when a dependency has no wheel, inspect its build configuration and version before the first install.
2. Build any required source distribution in an isolated, disposable environment (a container), never on a machine holding secrets.
3. Pin the exact version and hash of what was reviewed, and commit it.
4. Run a clean, hash-checked install in CI and verify the test suite still passes.

**Point-in-time note:** installer defaults and flags change. Verify commands against the
pinned tool's current documentation before relying on them.

**Vendored static assets:**

- [ ] Every vendored `.js` / `.css` file has a recorded source, version and SHA-256
- [ ] Updates to vendored files are reviewed as diffs, not replaced blindly
- [ ] Assets loaded from a third-party origin (if any) carry `integrity` and `crossorigin` attributes

**Supply-chain hygiene** (advisory audits do not catch newly malicious packages):

- [ ] Exactly one authoritative pinned dependency set per project root is committed, and CI never rewrites it
- [ ] Critical and high findings triaged for reachability; deferrals have a reason and review date
- [ ] Bulk automated upgrades are never merged blindly; each upgrade's changelog and test run are reviewed
- [ ] Provenance and attestations verified where the package index supports them
- [ ] New dependencies reviewed for ownership, maintenance, release age, provenance, transitive graph and typosquatting — the standard library considered first
- [ ] Every dependency change recorded in `CHANGELOG.md` under `## [Unreleased]` (`Security` for advisories)

## AI / LLM Security

For any feature that calls an LLM (chat, summaries, agents, retrieval):

- [ ] Model output treated as untrusted — never into `eval`, SQL, a shell, `| safe`, `innerHTML` or file paths
- [ ] Prompt injection assumed; permissions enforced in code through the Gate, not in the system prompt
- [ ] Secrets, cross-tenant data and full system prompts kept out of the context window
- [ ] Tool and agent permissions scoped; destructive or irreversible actions require confirmation
- [ ] Token, rate and recursion or loop limits set (bounded consumption)
- [ ] Retrieval scoped per tenant at query time; documents validated before indexing
- [ ] Personal data sent to a model provider only with a legal basis and a data-processing agreement

## Error Handling

```python
# Production (APP_DEBUG=false): a stable code and a translation key, no internals
return self.json(
    {"error": {"code": "INTERNAL_ERROR", "message_key": "error.generic", "params": {}}},
    status=500,
)
```

```python
# NEVER in production:
return self.json(
    {
        "error": str(exc),                          # exposes internals
        "trace": traceback.format_exc(),            # exposes code paths
        "query": failed_sql,                        # exposes schema
    },
    status=500,
)
```

- [ ] `APP_DEBUG=false` in production — the exception handler only attaches traces to 5xx responses when debug is on
- [ ] Domain errors are typed exceptions carrying `code` + `message_key`; the rendered sentence lives in the translation store (`en`, `pt-BR`, `es`)
- [ ] Authorization failures return the same response whether the resource exists or not, where existence is itself sensitive
- [ ] The full exception goes to the log with `request_id`, entity id and user id — not to the client
- [ ] No bare `except:` or `except Exception:` swallowing a security failure

## OWASP Top 10 Quick Reference

| # | Vulnerability | Prevention in Craft |
|---|---|---|
| 1 | Broken Access Control | `auth` / `api` / `role:` / `permission:` middleware, Gate and Policy ownership checks on every action |
| 2 | Cryptographic Failures | HTTPS, `Hash.make()`, `hmac.compare_digest`, real `APP_KEY`, no secrets in code |
| 3 | Injection | Query builder bindings, SQL only in repositories, `FormRequest` validation, Forge escaping |
| 4 | Insecure Design | Threat modeling, spec-driven development, abuse cases as tests |
| 5 | Security Misconfiguration | `APP_DEBUG=false`, CSP and HSTS configured, secure cookies, minimal permissions |
| 6 | Vulnerable Components | Pinned hash-checked installs, `pip-audit`, minimal dependencies, reviewed vendored assets |
| 7 | Authentication Failures | `throttle` on auth routes, session regeneration on login, cooldowns, MFA for sensitive actions |
| 8 | Data Integrity Failures | Signed sessions and tokens, verified dependencies and assets, `@csrf` on state changes |
| 9 | Logging Failures | `security_events` and `auth_audit_logs`, structured logs with `request_id`, no secrets in logs |
| 10 | SSRF | Allowlisted outbound URLs, private addresses rejected, redirects disabled |

## OWASP Top 10 for LLMs Quick Reference

For applications with LLM features (OWASP GenAI Security Project, 2025 list).

| ID | Risk | Prevention |
|---|---|---|
| LLM01 | Prompt Injection | Do not treat the system prompt as a boundary; enforce permissions in code |
| LLM02 | Sensitive Information Disclosure | Keep secrets and personal data out of prompts; filter outputs |
| LLM03 | Supply Chain | Vet models, datasets and plugins like any dependency |
| LLM04 | Data and Model Poisoning | Use trusted model sources, verify integrity; vet fine-tuning and retrieval data |
| LLM05 | Improper Output Handling | Treat model output as untrusted; validate, bind, escape |
| LLM06 | Excessive Agency | Scope tool permissions; confirm destructive actions |
| LLM07 | System Prompt Leakage | Assume the system prompt can leak; put no secrets in it |
| LLM08 | Vector and Embedding Weaknesses | Scope retrieval per tenant; validate documents before indexing |
| LLM09 | Misinformation | Ground answers with citations; validate critical claims; keep a human in the loop |
| LLM10 | Unbounded Consumption | Cap tokens, request rate and loop or recursion depth |

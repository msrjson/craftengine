---
name: security-and-hardening
description: Hardens Craft Engine code against vulnerabilities, from threat model to verified controls. Use when handling untrusted input, authentication, sessions, authorization, data storage, file uploads, webhooks or external integrations, when checking a flow against the OWASP Top 10, when triaging dependency audit findings or supply-chain risk, or when personal data and privacy compliance (LGPD, GDPR, CCPA) are involved.
---

# Security and Hardening

## Overview

Security-first development for Craft Engine applications. Treat every external input as
hostile, every secret as sacred, and every authorization check as mandatory. Security is not
a phase at the end of a project — it is a constraint on every line that touches user data,
authentication, money or an external system.

Craft ships most of the controls you need: `VerifyCsrfToken`, signed sessions,
`SecurityHeaders`, `ThrottleRequests`, `Firewall`, `AntiSpam`, `Honeypot`, the Gate with
Policies, `FormRequest` validation and password hashing. A control that ships is not a
control that is on. This skill is about using them correctly, configuring the ones that are
off by default, and closing the gaps they do not cover.

## When to Use

- Building anything that accepts user input (forms, JSON bodies, query strings, headers)
- Implementing authentication, sessions or authorization
- Storing or transmitting sensitive or personal data
- Integrating with external APIs, webhooks or callbacks
- Adding file uploads or anything that reads, moves or deletes files
- Handling payments (`bank_slip`, `PIX`, cards) or personal data (`CPF`, e-mail, address)
- Adding a dependency, or triaging a dependency audit
- Adding a feature that calls an LLM

## Process: Threat Model First

Controls bolted on without a threat model are guesses. Before hardening, spend five minutes
thinking like an attacker:

1. **Map the trust boundaries.** Where does untrusted data cross into the system? HTTP
   requests, form fields, uploads, webhooks, third-party APIs, queue payloads, and **LLM
   output** — plus values that look internal because the OS handed them to you: another
   process's command line or environment, file names on a shared volume, a path inside a
   job payload. Trust follows who *wrote* a value, not which channel delivered it. Every
   boundary is attack surface.
2. **Name the assets.** What is worth stealing or breaking? Credentials, `APP_KEY`, personal
   data, payment data, admin actions, tenant isolation, money movement.
3. **Run STRIDE over each boundary** — a quick lens, not a ceremony:

| Threat | Ask | Typical mitigation in Craft |
|---|---|---|
| **S**poofing | Can someone impersonate a user or service? | `auth` / `api` middleware, signed sessions, webhook signature check with `hmac.compare_digest` |
| **T**ampering | Can data be altered in transit or at rest? | Query builder bindings, `@csrf`, HTTPS, signed payloads |
| **R**epudiation | Can an action be denied later? | Audit rows (`security_events`, `auth_audit_logs`), structured logs with `request_id` |
| **I**nformation disclosure | Can data leak? | `hidden` on models, API Resources with explicit fields, generic errors, `APP_DEBUG=false` |
| **D**enial of service | Can it be overwhelmed? | `throttle`, input size rules (`max:`), timeouts on outbound calls |
| **E**levation of privilege | Can a user gain rights they should not? | Gate / Policy checks, `role:` / `permission:` middleware, `fillable` allowlists |

4. **Write abuse cases next to use cases.** For each feature ask "how would I misuse this?" —
   then make that the first `pytest` case (see `.claude/skills/test-driven-development/SKILL.md`).

If you cannot name the trust boundaries for a feature, you are not ready to secure it. This
is OWASP **A04: Insecure Design** — most breaches begin in design, not in code. Record the
threat model in the spec (`.claude/skills/spec-driven-development/SKILL.md`).

## The Three-Tier Boundary System

### Always Do (No Exceptions)

- **Validate all external input** at the boundary — a `FormRequest` (`app/Http/Requests`)
  or a `Validator` in the controller entry, never deep inside a service
- **Use query builder bindings** — `where()` and `DB.select(sql, bindings)`; never format
  user input into SQL (and SQL never lives in controllers or services anyway)
- **Let Forge escape output** — `{{ value }}` is escaped; do not bypass it for user data
- **Put `@csrf` in every state-changing form** and keep `VerifyCsrfToken` in the global stack
- **Put `@honeypot` / `@antispam` in every public form** (or set `antispam = True` on its `FormRequest`)
- **Use HTTPS** for all external communication; set `SESSION_SECURE_COOKIE=true` in production
- **Hash passwords** with `Hash.make()` / `Hash.check()` — never store or compare plaintext
- **Compare secrets in constant time** — `hmac.compare_digest`, never `==`
- **Authorize every protected action** through the Gate or a Policy, not only authenticate it
- **Configure CSP and HSTS** — `SecurityHeaders` only emits them when configured
- **Run a dependency audit** against the pinned dependency set before every release

### Ask First (Requires Human Approval)

- Adding new authentication flows or changing auth logic (`make:auth` output included)
- Storing new categories of sensitive data (personal data, payment data, government IDs)
- Adding new external service integrations
- Changing CORS behavior or the `VerifyCsrfToken` exempt paths (`api/*` by default)
- Adding file upload handlers
- Modifying rate limits, firewall thresholds or whitelist entries
- Granting elevated permissions or roles (`python dev.py role`, `permission`, `group`)

### Never Do

- **Never commit secrets** (`.env`, `APP_KEY`, API keys, database passwords, tokens)
- **Never log sensitive data** (passwords, tokens, session ids, full card numbers, full `CPF`)
- **Never trust client-side validation** (vanilla JS checks are UX, not a boundary)
- **Never disable security middleware** for convenience (`SESSION_CSRF=false` on a site with forms)
- **Never use `eval()`, `exec()`, `pickle.loads()` or `yaml.load()`** on untrusted data
- **Never assign `innerHTML`** with user-provided data in static `.js` files
- **Never store auth tokens in `localStorage`** — the session cookie is `httponly`
- **Never run with `APP_DEBUG=true` in production** — 5xx responses then carry stack traces
- **Never set `guarded = False`** on a model to make mass assignment "just work"

## OWASP Top 10 Prevention Patterns

These are prevention patterns, not a ranking. For the 2021 ordering, see the quick-reference
table in `.claude/references/security-checklist.md`.

### Injection (SQL, OS Command, Template)

```python
# BAD: SQL built from user input — injection, and SQL leaking into a service
rows = DB.select(f"SELECT * FROM orders WHERE customer_id = '{customer_id}'")

# GOOD: query builder with bound values, inside a repository
class OrderRepository:
    """Reads orders from storage."""

    def for_customer(self, customer_id: int) -> list[Order]:
        """Return the customer's orders, newest first.

        Args:
            customer_id: Primary key of the owning customer.

        Returns:
            The matching orders.
        """
        return Order.where("customer_id", customer_id).order_by_desc("created_at").get()

# GOOD: raw SQL when the builder cannot express it — bindings, never formatting
rows = DB.select("SELECT id FROM orders WHERE customer_id = ?", [customer_id])
```

For OS commands, call `subprocess.run([...], shell=False)` with an argument list and an
allowlisted executable; never build a shell string from input.

### Broken Authentication

```python
from craft.auth.password import Hash

hashed = Hash.make(plaintext)          # bcrypt, PBKDF2-HMAC-SHA256 fallback
is_valid = Hash.check(plaintext, user.get_attribute("password"))
if is_valid and Hash.needs_rehash(user.get_attribute("password")):
    user.update({"password": Hash.make(plaintext)})
```

Session settings live in `config/session.py` and are driven by the environment:

```ini
# .env (production)
SESSION_DRIVER=file            # only a signed id in the cookie
SESSION_LIFETIME=7200          # seconds
SESSION_SECURE_COOKIE=true     # HTTPS only — defaults to false
SESSION_SAME_SITE=lax          # blocks the cookie on cross-site POSTs
SESSION_CSRF=true              # never false on a site that renders forms
```

`StartSession` always sets the cookie `httponly`. The session is signed with `APP_KEY`
(`python dev.py key:generate`); a missing key in production is a boot failure, not a warning
to ignore. `Auth.login()` regenerates the session id — never log a user in by writing
`auth_user_id` into the session yourself, or you reintroduce session fixation.

Throttle authentication routes:

```python
Route.post("/login", [LoginController, "store"]).middleware("throttle").name("login.attempt")
```

`throttle` is a fixed window of 10 attempts per 60 seconds per IP and path, counted in the
cache store. To change the numbers, subclass `ThrottleRequests` and register it with
`kernel.alias_middleware(...)` rather than editing the default.

### Cross-Site Scripting (XSS)

```html
{# BAD: disabling escaping on user content #}
<div>{{ comment.body | safe }}</div>

{# GOOD: Forge escapes by default #}
<div>{{ comment.body }}</div>
```

```js
// BAD (static .js): user content parsed as markup
element.innerHTML = payload.displayName;

// GOOD: text, never markup
element.textContent = payload.displayName;
```

If rich HTML from users is a real requirement, sanitize it server-side against a strict tag
and attribute allowlist before storing, keep a `no_html` rule on fields that must not carry
markup, and still ship a CSP that forbids inline script.

### Broken Access Control

Authentication says who the user is; authorization says whether they may do *this* to
*this* record. Check both, on every action.

```python
# app/Policies/TaskPolicy.py
class TaskPolicy:
    """Authorization rules for tasks."""

    def update(self, user: User | None, task: Task) -> bool:
        """Allow the owner to update the task.

        Args:
            user: The authenticated user, or None for a guest.
            task: The task being modified.

        Returns:
            True when the user owns the task.
        """
        if user is None:
            return False
        return user.get_attribute("id") == task.get_attribute("owner_id")
```

```python
# app/Providers/AuthServiceProvider.py — boot()
Gate.policy(Task, TaskPolicy)

# Controller action: thin, delegates to the Gate and a container-resolved service
def update(self, request: Request, task_id: int) -> Response:
    """Update a task the current user owns."""
    task = Task.find_or_fail(task_id)
    Gate.authorize("update", request.user(), task)   # raises AuthorizationException (403)
    data = UpdateTaskRequest(request).validated()
    return self.json(TaskResource(self.tasks.update(task, data)).to_dict())
```

The Gate denies by default: an ability with no closure, no Policy method and no matching
permission grant is a refusal. Route middleware (`auth`, `role:admin`,
`permission:manage-users`) is the first line; the Gate check inside the action is the second,
so a forgotten alias on one route does not expose the record. Scope every query by owner or
tenant — `find(id)` on user-supplied ids without an ownership check is IDOR.

### Security Misconfiguration

The global stack in `bootstrap/app.py` ships `RequestContext`, `SecurityHeaders`,
`StartSession`, `SetLocale`, `VerifyCsrfToken` and `Authenticate`. Keep that order: the
session must exist before CSRF verification, and `VerifyCsrfToken` raises if it runs without
one.

`SecurityHeaders` always sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and
`Referrer-Policy: strict-origin-when-cross-origin`. **CSP and HSTS are only sent when
configured** — add them through a config module, which the repository exposes as
`security.csp` and `security.hsts`:

```python
# config/security.py
from craft.config import env

csp = env(
    "SECURITY_CSP",
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
)
hsts = env("SECURITY_HSTS", "max-age=31536000; includeSubDomains")
```

Headers are applied with "set if absent", so a response that already carries a header keeps
its own value. Because the frontend is vendored static `.js` and `.css`, a strict CSP with no
`'unsafe-inline'` is achievable — keep scripts in files, not in template `<script>` blocks.

Cross-origin access: routes under `api/*` are exempt from CSRF by default, so they must be
protected by the `api` bearer-token middleware instead. If a browser on another origin must
call the API, allow exactly the known origins — never reflect the `Origin` header and never
combine a wildcard origin with credentials.

Production configuration: `APP_DEBUG=false`, a real `APP_KEY`, `SESSION_SECURE_COOKIE=true`,
`METRICS_ENABLED` either off or protected by `METRICS_TOKEN` and a private network.

### Sensitive Data Exposure

```python
class User(Model):
    """An account that can sign in."""

    fillable = ["name", "email"]
    hidden = ["password", "api_token", "remember_token"]
```

`to_dict()` drops `hidden` attributes. Prefer an API Resource (`make:resource`) that lists
the fields a client may see over serializing the model — an allowlist does not leak the next
column someone adds.

```python
# Secrets come from the environment, and absence fails fast at boot
api_key = env("PAYMENT_GATEWAY_KEY")
if not api_key:
    raise ConfigurationError(code="PAYMENT_GATEWAY_KEY_MISSING")
```

API tokens are stored as SHA-256 digests: `AuthenticateApiToken` looks up the hashed value
first. Issue new tokens hashed and migrate any plaintext tokens; the plaintext fallback exists
for compatibility, not as a pattern.

### Server-Side Request Forgery (SSRF)

Any time the server fetches a URL the user influenced — webhooks, "import from URL", image
proxies, link previews — an attacker can aim it at internal services (cloud metadata,
`localhost`, private networks, the PostgreSQL port).

```python
import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_HOSTS: frozenset[str] = frozenset({"hooks.example.com"})


def assert_safe_url(raw: str) -> str:
    """Validate an outbound URL against the allowlist and private ranges.

    Args:
        raw: The URL supplied by, or derived from, a user.

    Returns:
        The URL, unchanged, when it is safe to fetch.

    Raises:
        UnsafeOutboundUrlError: When the scheme, host or any resolved address is not allowed.
    """
    parts = urlsplit(raw)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise UnsafeOutboundUrlError(code="OUTBOUND_URL_NOT_ALLOWED")
    infos = socket.getaddrinfo(parts.hostname, parts.port or 443, proto=socket.IPPROTO_TCP)
    if any(not ipaddress.ip_address(info[4][0]).is_global for info in infos):
        raise UnsafeOutboundUrlError(code="OUTBOUND_URL_PRIVATE_ADDRESS")
    return raw
```

`is_global` is false for loopback, link-local `169.254.169.254` (cloud metadata, the first
SSRF target), private and unique-local ranges, across IPv4 and IPv6. Fetch with redirects
disabled and a short timeout. This belongs in `app/plugins/` as a shared capability, resolved
from the container — not copied into each module.

**Caveat — TOCTOU gap.** The HTTP client resolves DNS again after the check, so a short-TTL
record can rebind to an internal address between validation and connection. For high-risk
surfaces, connect to the pinned address you validated (sending the original `Host` header and
SNI), or route outbound traffic through an egress proxy that enforces the same rules.

`FirewallMiddleware` pattern-matches SSRF targets in the URI and query string. That is a
tripwire that feeds `security_events`, not a substitute for validating the URL you fetch.

## Input Validation Patterns

### Schema Validation at Boundaries

```python
# app/Http/Requests/StoreTaskRequest.py
class StoreTaskRequest(FormRequest):
    """Authorizes and validates task creation."""

    def authorize(self) -> bool:
        """Only authenticated users may create tasks."""
        return self.user() is not None

    def rules(self) -> dict[str, list[str]]:
        """Validation rules for the task payload."""
        return {
            "title": ["required", "string", "max:200", "no_html"],
            "description": ["nullable", "string", "max:2000"],
            "priority": ["required", "in:low,medium,high"],
            "due_at": ["nullable", "date"],
        }
```

```python
def store(self, request: Request) -> Response:
    """Create a task from validated input."""
    data = StoreTaskRequest(request).validated()   # 403 or 422 before any logic runs
    task = self.tasks.create(owner=request.user(), data=data)
    return self.json(TaskResource(task).to_dict(), status=201)
```

`validated()` authorizes, runs the anti-spam check when enabled, validates, and returns
**only the fields that were ruled on** — unknown keys never reach the service. Pass that dict,
never `request.all()`, to `create()` / `update()`, and keep `fillable` as a second allowlist.
Error copy shown to users is a translation key with `en`, `pt-BR` and `es` rows; API errors
carry `code` + `message_key`.

### Public Forms

```html
<form method="POST" action="/contact">
    @csrf
    @honeypot
    <label for="message">{{ __('contact.form.field.message') }}</label>
    <textarea id="message" name="message" maxlength="2000"></textarea>
    @error('message') <p class="field-error">{{ message }}</p> @enderror
    <button type="submit">{{ __('contact.form.action.send') }}</button>
</form>
```

On the server, set `antispam = True` (and `antispam_action`) on the `FormRequest` or call
`AntiSpam.validate(request, action="contact")`. Detections are written to `security_events`
without interrupting the response, and reviewed with `python dev.py security:audit` and
`python dev.py firewall:list`.

### File Upload Safety

```python
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp"})
MAX_UPLOAD_KILOBYTES = 5 * 1024


class StoreAvatarRequest(FormRequest):
    """Validates an avatar upload."""

    def rules(self) -> dict[str, list[str]]:
        """Type and size are enforced before the file is touched."""
        return {
            "avatar": ["required", "image", "mimes:jpg,jpeg,png,webp", f"max_file_size:{MAX_UPLOAD_KILOBYTES}"],
        }
```

- Do not trust the extension or the client-sent content type: `image` and `mimes` read the file
  name and declared type, so verify magic bytes for anything critical, and re-encode images
  through the `Image` service (`optimize(strip_exif=True)`) to drop metadata
- Generate the stored file name server-side (a UUID); never reuse the uploaded name as a path
- Store uploads outside the web root, serve them through a controller that authorizes access
- Cap request body size at the proxy as well as in the rules

### Destructive Operations on Derived Paths

A delete, move or overwrite is only as safe as the value that names its target. Reading that
value from the OS, a job payload or a sibling service proves where it *arrived from*, not who
*wrote* it — another process's command line is as attacker-controlled as a form field. A shape
check ("absolute path, at least one directory deep") proves well-formedness and gets mistaken
for authorization; that is how a cleanup routine deletes the root instead of the leaf.

Before a destructive call, require all three: the resolved target sits under an **allowlisted
root** (compare after resolving symlinks with `Path.resolve(strict=True)`, never on the raw
string); it is at least one level **below** that root, so a root is never itself the target;
and it carries **evidence that it is yours**, read *before* the operation and before any
teardown that removes it — otherwise "absent" and "not mine" are indistinguishable. On
refusal, log the rejected target and stop: a cleanup that falls back to a broader default
path is the failure this guards against. Worked example in
`.claude/references/security-checklist.md`.

Two limits, because the check reads stronger than it is. A marker inside the tree is
self-attestation — anything that can write there can write the marker — so the expected owner
has to come from authenticated state, and the marker needs integrity protection (restrictive
ownership, or an HMAC keyed with a secret the writer does not hold) before it counts as
authorization. And resolving a path and then operating on the *name* is a check/use race
wherever an untrusted process can swap an ancestor: on a shared volume, hold the target by
descriptor (`os.open` with `O_NOFOLLOW`, `dir_fd=` operations) or make sure the hierarchy
cannot change for the duration.

## Triaging Dependency Audit Results

Dependency audits report known advisories; they do not prove a package is trustworthy or that
the vulnerable code is reachable. Use this decision tree:

```text
The dependency audit (pip-audit or equivalent) reports a vulnerability
├── Severity: critical or high
│   ├── Is the vulnerable code reachable in runtime, build, test or deployment paths?
│   │   ├── YES --> Fix immediately (upgrade, patch, or replace the dependency)
│   │   └── NO (confirmed unused across those paths) --> Fix soon, but not a blocker
│   └── Is a fix available?
│       ├── YES --> Upgrade to the patched version
│       └── NO --> Look for a workaround, consider replacing the dependency, or record an
│                  exception with a reason and a review date
├── Severity: moderate
│   ├── Reachable in production? --> Fix in the next release
│   └── Dev or test only? --> Fix when convenient, track in the backlog
└── Severity: low
    └── Track and fix during regular dependency updates
```

**Key questions:**

- Is the vulnerable function actually called on your code path?
- Is the dependency a runtime dependency or a dev/test-only one?
- Is it exploitable in your deployment context (a vulnerability in a client you never run)?

When you defer a fix, record the reason and review date, and add the upgrade to
`CHANGELOG.md` under `## [Unreleased]` (`Security`) in the change that lands it.

### Supply-Chain Hygiene

Craft is pure Python: dependencies are declared in `pyproject.toml`, and the frontend is
vendored static files — there is no Node toolchain and no package manager for JavaScript.
Keep it that way; a new build pipeline is a new supply chain.

1. **Find the installation boundary.** The project root that owns `pyproject.toml` and the
   pinned dependency set (a lock or constraints file, whichever the project commits) is the
   install root. CI installs from exactly that set. Two competing pin files at one root is a
   defect: stop and pick one.
2. **Install reproducibly.** Pin exact versions, prefer hash-checked installs
   (`pip install --require-hashes -r <pinned file>`), and prefer wheels
   (`--only-binary :all:` where feasible) — building an sdist executes arbitrary code from the
   package at install time.
3. **Vendored static assets are dependencies too.** Record the source URL, version and
   SHA-256 of every vendored `.js` / `.css` file, and review the diff when it changes.

Audits only find known advisories; they do not catch a newly malicious or typosquatted
package. Therefore:

- **Never apply bulk automated upgrades blindly.** Preview each upgrade, read its changelog,
  and run `python -m pytest tests` against it; an upgrade can cross a declared compatibility range.
- **Verify provenance where the index supports it** (attestations, signed releases) and treat
  absence as a reason to look closer, not as proof of compromise.
- **Review new dependencies and pin-file diffs together** — ownership, maintenance, release
  age, provenance, transitive graph, and typosquats (`python-dateutil` vs `dateutil`)
  (OWASP **A06**, **LLM03**). Prefer the standard library first.

## Rate Limiting

```python
# routes/web.py
Route.post("/login", [LoginController, "store"]).middleware("throttle").name("login.attempt")
Route.post("/password/email", [PasswordResetController, "send"]).middleware("throttle")
```

`ThrottleRequests` counts in the configured **cache store**. That matters once more than one
process serves traffic: with the in-process `array` driver each worker keeps its own counter,
so the effective limit is `max_attempts × workers`, and a restart resets it. In production
use a shared driver (`redis`) so every instance counts against the same window.

Two further layers:

- `FirewallMiddleware` (`firewall` alias) blocks blacklisted IPs and scores payload signatures;
  a score past the threshold blacklists the IP. It reads the first `X-Forwarded-For` entry, so
  only enable it behind a proxy that overwrites that header — otherwise a client can choose its
  own IP.
- `Honeypot` tracks login cooldowns and decoy usernames in `auth_cooldowns` and
  `auth_audit_logs`.

## Secrets Management

```text
.env files:
  ├── .env.example  → Committed (placeholder values only)
  ├── .env          → NOT committed (real secrets, APP_KEY)
  └── .env.*.local  → NOT committed (local overrides)

.gitignore must include:
  .env
  .env.*.local
  *.pem
  *.key
  storage/logs/
  storage/framework/sessions/
```

**Always check before committing:**

```bash
git diff --cached | grep -iE "password|secret|api_key|token|app_key"
```

**If a secret is ever committed, rotate it.** Deleting the line or rewriting history is not
enough — assume it is compromised the moment it reaches a remote. Revoke and reissue first
(`python dev.py key:generate` for `APP_KEY`, knowing it invalidates existing sessions), then
purge it from history.

## Data Privacy & Compliance

Securing data answers "can an attacker read it?" Privacy answers "should *we* hold it at all,
and for how long?" — a separate question hardening does not answer. The cheapest data to
protect, breach and comply over is the data you never collected. Treat personal data as a
liability to minimize, not an asset to hoard. Privacy by design is mandatory in Craft
projects: a feature that processes personal data is not done until it complies with LGPD,
GDPR or CCPA as applicable.

**Know what you hold.** You cannot protect, or honor a deletion request for, data you cannot
find. Classify fields in the migration that adds them:

| Class | Examples | Handling |
|---|---|---|
| **Non-personal** | Aggregates, anonymized counts | Normal handling |
| **Personal** | Name, e-mail, IP address, device or user ids | Minimize, access-control, include in export and erasure |
| **Sensitive** | Health, finance, precise location, biometrics, government ids (`CPF`), anything about minors | Explicit legal basis, stricter access, often encryption and audit logging |

**Operating rules:**

- **Minimize and state a purpose.** Collect a field only against a stated use. "It might be
  useful later" is not a purpose — it is latent breach scope. Do not put personal data into
  telemetry (the `observability-and-instrumentation` skill,
  `.claude/skills/observability-and-instrumentation/SKILL.md`, makes the same point from the
  operations side).
- **Set retention up front, then actually erase.** Every personal-data store needs a retention
  period and a working erasure path — including backups, cache, search indexes and analytics
  copies. A scheduled job (`python dev.py schedule`) enforces it.
- **Reconcile erasure with soft deletes.** Business entities are soft-deleted (`deleted_at`,
  `is_active`), never physically removed. That preserves the business record — it does not
  satisfy an erasure request. Erasure means **anonymizing or pseudonymizing the personal
  fields** on the soft-deleted row, through a forward-only migration or a service, so the
  record survives and the person does not.
- **Support the data-subject rights your jurisdiction requires**: access, export, correction,
  erasure. These are engineering features — design the schema so a person's data is findable
  and erasable, not smeared irreversibly across tables.
- **Get consent before collection or third-party sharing**, and make it auditable. Sending
  personal data to an analytics, advertising or LLM vendor is sharing; the user's choice gates
  it and the vendor needs a data-processing agreement.
- **Make jurisdiction a configuration boundary**, not an assumption. Consent and legal texts
  are per-jurisdiction documents referenced by identifier, never machine-translated copy.

When data crosses a trust boundary, validate it as untrusted (Input Validation above); when a
privacy incident exposes personal data, the breach-notification clock is part of the
postmortem — follow `.claude/skills/debugging-and-error-recovery/SKILL.md`.

This guidance is engineering practice, not legal advice.

## Securing AI / LLM Features

If the application calls an LLM (through the `AI` or `Agent` services, or any provider) —
chat, summaries, agents, retrieval — it inherits a new attack surface. Map it to the OWASP
Top 10 for LLM Applications (2025):

- **Treat all model output as untrusted input (LLM05: Improper Output Handling).** Never pass
  it into `eval`, SQL, a shell, `| safe` in a template, `innerHTML` or a file path. Validate
  and encode it exactly as raw user input.
- **Assume prompts can be hijacked (LLM01: Prompt Injection).** Untrusted text in the context —
  a user message, a fetched page, a PDF — can carry instructions. The system prompt is not a
  security boundary; enforce permissions in code, through the Gate.
- **Keep secrets and other users' data out of prompts (LLM02 / LLM07).** Anything in the
  context can be echoed back. No API keys, no cross-tenant rows, no full system prompt where
  the model can repeat it.
- **Constrain tool and agent permissions (LLM06: Excessive Agency).** Scope tools to the
  minimum, require confirmation for destructive or irreversible actions, validate every tool
  argument, and authorize each tool call as the requesting user.
- **Bound consumption (LLM10: Unbounded Consumption).** Cap tokens, request rate and loop or
  recursion depth so a crafted input cannot run up cost or hang a worker.
- **Isolate retrieval data (LLM08: Vector and Embedding Weaknesses).** Treat the vector store as
  a trust boundary: scope embeddings per tenant at query time so one tenant cannot retrieve
  another's data, and validate documents before indexing so poisoned content cannot steer answers.

```python
# BAD: model output as a command and as markup
sql = ai_client.generate(prompt_for(question))
DB.select(sql)                                    # arbitrary query execution
return self.view("answer", {"html": reply})       # rendered with | safe: stored XSS via the model

# GOOD: model output is data — parse, validate against an allowlist, then act
try:
    intent = AssistantIntent.model_validate_json(ai_client.generate_json(prompt_for(question)))
except ValidationError as error:
    raise UnexpectedModelOutputError(code="AI_OUTPUT_INVALID") from error
self.actions.run_allowlisted(intent.action, intent.params, user=request.user())
return self.view("answer", {"text": reply})       # escaped by Forge
```

## Security Review Checklist

```markdown
### Authentication
- [ ] Passwords hashed with `Hash.make()`; verified with `Hash.check()`; rehash when needed
- [ ] Session cookie httponly, `SESSION_SECURE_COOKIE=true`, `SESSION_SAME_SITE=lax` or strict
- [ ] Login, registration and password reset routes carry `throttle`
- [ ] Password reset tokens are single-use and expire (1 hour or less)
- [ ] Session id regenerated on login (`Auth.login()`), invalidated on logout

### Authorization
- [ ] Every protected route carries `auth` / `api` / `role:` / `permission:` middleware
- [ ] Every action on a record checks ownership through the Gate or a Policy (no IDOR)
- [ ] Admin actions verify the role inside the action as well as on the route
- [ ] Tenant-scoped queries cannot return another tenant's rows

### Input
- [ ] All input validated at the boundary with a `FormRequest` or `Validator`
- [ ] Only `validated()` data reaches `create()` / `update()`; models declare `fillable`
- [ ] No SQL built by string formatting; SQL only in repositories, with bindings
- [ ] Every state-changing form has `@csrf`; every public form has `@honeypot` / `@antispam`
- [ ] No `| safe` on user content; no `innerHTML` with user content in static `.js`
- [ ] Redirect targets validated against an allowlist (no open redirect)
- [ ] Server-side URL fetches allowlisted, private addresses rejected (no SSRF)
- [ ] Delete/move/overwrite targets built from data: symlinks resolved, allowlisted root, minimum depth, ownership evidence read before the operation

### Data
- [ ] No secrets in code or version control; `.env` ignored
- [ ] Sensitive attributes in `hidden`; APIs return Resources with explicit fields
- [ ] API tokens stored hashed
- [ ] Secrets and tokens compared with `hmac.compare_digest`
- [ ] Personal data classified, collected against a stated purpose, minimized
- [ ] Personal data has a retention period and a working erasure (anonymization) path, including backups and caches
- [ ] Export and erasure requests supported where required; third-party sharing has consent

### Infrastructure
- [ ] `APP_DEBUG=false` and a real `APP_KEY` in production
- [ ] `SecurityHeaders` in the global stack; `security.csp` and `security.hsts` configured
- [ ] Cross-origin access restricted to known origins
- [ ] Throttle counters in a shared cache driver when more than one instance runs
- [ ] `/metrics` disabled or protected by `METRICS_TOKEN` and network policy
- [ ] Error responses carry `code` + `message_key`, no internals

### Supply Chain
- [ ] One authoritative pinned dependency set; CI installs exactly that set, hash-checked where possible
- [ ] Audit findings triaged by reachability; deferrals have a reason and review date
- [ ] New dependencies and vendored assets reviewed (ownership, provenance, release age, transitive graph)

### AI / LLM (if used)
- [ ] Model output treated as untrusted (no eval, SQL, shell, `| safe`, `innerHTML`)
- [ ] Secrets and other users' data kept out of prompts
- [ ] Tool and agent permissions scoped; destructive actions require confirmation
```

## See Also

For the detailed checklist, security headers, the destructive-path worked example and the
OWASP quick references, see `.claude/references/security-checklist.md`. For a structured
audit of a change, invoke the `security-auditor` agent (`.claude/agents/security-auditor.md`).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "This is an internal tool, security doesn't matter" | Internal tools get compromised. Attackers target the weakest link. |
| "We'll add security later" | Retrofitting security is many times harder than building it in. Add it now. |
| "No one would try to exploit this" | Automated scanners will find it. Obscurity is not security. |
| "The framework handles security" | The framework ships the tools, and some are off by default (CSP, HSTS, secure cookies). You still configure and use them. |
| "The route has `auth`, so it's protected" | Authentication is not authorization. Without a Gate or Policy check, any signed-in user can edit any record. |
| "It's just a prototype" | Prototypes become production. Security habits from day one. |
| "Threat modeling is overkill here" | Five minutes of "how would I attack this?" prevents the design flaws no control can patch later. |
| "It's just LLM output, it's only text" | That text can be a SQL statement, a script tag or a shell command. Treat it like any untrusted input. |
| "The audit passed, so the dependency is safe" | Audits match known advisories. They do not detect a newly malicious package or a compromised release. |
| "Collect it now, we might need it later" | Data you don't hold can't be breached, subpoenaed or mis-deleted. "Might need it" is breach scope, not a purpose. |
| "Soft delete covers the erasure request" | A soft-deleted row still holds the personal data. Anonymize the personal fields; keep the business record. |
| "Compliance is legal's problem, not ours" | Export, erasure, retention and consent are schema and code. Legal cannot bolt them on afterwards. |

## Red Flags

- User input formatted into SQL, a shell command, a file path or a template rendered with `| safe`
- A controller or service calling `DB.select` / `DB.statement` directly
- A POST form without `@csrf`, or a public form without `@honeypot` / `@antispam`
- `request.all()` passed to `create()` or `update()`; a model with `guarded = False`
- A route with `auth` but no ownership check on the record it modifies
- A delete, move or overwrite whose target comes from a payload, a config value or another process's command line, guarded only by a shape check on the path
- Secrets in source code or commit history; `APP_DEBUG=true` in a production `.env`
- Token or signature compared with `==`
- `SESSION_SECURE_COOKIE` unset in production; `SESSION_CSRF=false` on a site with forms
- No `throttle` on authentication routes, or throttle counters in a per-process cache with several workers
- `FirewallMiddleware` enabled without a proxy that overwrites `X-Forwarded-For`
- Stack traces or exception messages in responses to users
- Dependencies with known critical vulnerabilities, unpinned installs, or a new Node build pipeline
- Server fetches user-supplied URLs without an allowlist (SSRF)
- LLM output passed into a query, a template with `| safe`, a shell or `eval`
- Secrets, personal data or the full system prompt inside an LLM context window
- Personal data collected with no stated purpose, retention period or erasure path
- Personal data sent to analytics, advertising or LLM vendors without consent or a data-processing agreement
- "Delete my account" that only sets `deleted_at` while the personal data lingers in rows, caches and backups

## Verification

After implementing security-relevant code:

- [ ] The dependency audit has no unmitigated reachable critical or high findings; CI installs the pinned set
- [ ] No secrets in source code or git history
- [ ] All input validated at the boundary; only validated fields reach persistence
- [ ] `@csrf` on every state-changing form; `@honeypot` / `@antispam` on public forms
- [ ] Destructive filesystem operations resolve symlinks, then verify allowlisted root, minimum depth and ownership before running
- [ ] Authentication and authorization checked on every protected action, with a `pytest` case proving another user gets 403
- [ ] Security headers present in responses, CSP and HSTS included (check with Chrome DevTools, Network panel)
- [ ] Error responses carry `code` + `message_key` and expose no internals
- [ ] Rate limiting active on authentication routes, backed by a shared cache store when more than one instance serves traffic
- [ ] Server-side URL fetches validated against an allowlist (no SSRF)
- [ ] LLM output validated and encoded before use (if AI features are present)
- [ ] Personal data classified, minimized to a stated purpose, with a retention period
- [ ] Export and erasure requests work end to end (including backups, cache and analytics copies)
- [ ] Gates pass: `python -m pytest tests`, `ruff check engine`, `python .claude/rules/lint_language.py`, `python .claude/rules/lint_structure.py`
- [ ] `CHANGELOG.md` has the change under `## [Unreleased]`, in `Security` where it applies

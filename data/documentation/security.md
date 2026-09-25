# Authentication & Security

Craft contains modular authentication and authorization components mapped to clean, static facade accessors. It also ships optional security utilities — a Post-Quantum Cryptography (PQC) token-signing helper and a CAPTCHA integration — that you wire in explicitly where needed. **Session cookies do not use PQC**: they are signed with HMAC-SHA256 (see [Sessions and CSRF](#sessions-and-csrf) below).

---

## Authentication (Auth Facade)

Use the `Auth` facade to authenticate user credentials and query the current session state:

```python
from craft.facades import Auth

# Attempt authentication using login attributes
if Auth.attempt({"email": "user@craft.io", "password": "securepassword"}):
    # Retrieve current authenticated User model instance
    user = Auth.user()
    print(f"Authenticated as {user.name}")

# Check if a user session is active
if Auth.check():
    # Logout current user session
    Auth.logout()
```

---

## User Roles & Types

Craft supports three user roles/types out-of-the-box:
1. **User (`user`)**: A standard user account.
2. **Admin (`admin`)**: A system administrator account with full administrative credentials.
3. **Tenant (`tenant`)**: A tenant account representing an isolated workspace/SaaS client.

### Checking the User Type
The `users` table carries a `type` column (`user`, `admin`, `tenant`) and an `is_admin` flag. Read them like any other attribute:

```python
user = Auth.user()

if user.get_attribute("is_admin"):
    # Perform administrator actions
    pass

if user.get_attribute("type") == "tenant":
    # Perform tenant actions
    pass
```

For anything richer than a column check, define a gate (below) and ask the gate instead.

---

## Authorization & Gates (Gate Facade)

Authorization checks allow or deny requests based on user permissions.

### Defining Gates
Gates are closure callbacks mapped to action permissions (typically declared inside `AppServiceProvider` or a dedicated provider):

```python
from craft.facades import Auth, Gate

# Define a gate rule
Gate.define("publish-posts", lambda user: user.get_attribute("is_admin"))

# Check the gate permissions in a controller — the user is always passed explicitly
if not Gate.allows("publish-posts", Auth.user()):
    return self.json({"message": "Unauthorized"}, status=403)
```

`Gate.allows(ability, user, *args)` requires the user as the second argument;
`Gate.denies(...)` is its negation, and `Gate.authorize(...)` raises an
`AuthorizationException` (403) instead of returning `False`.

`Gate.allows` checks, in order: (1) a registered ability closure, (2) a policy
on the target model, (3) the RBAC permission system — `user.has_permission(ability)`,
if the user carries that method — before denying by default. That third tier
means a permission slug like `"manage-users"` works as a Gate ability without
anyone having to register a closure for it. See [Authorization
(RBAC)](authorization.md) for roles, permissions, and the `role:`/`permission:`
route middleware built on top of it.

---

## Authorization Policies

Policies organize authorization checks around specific models.

### Example Policy
```python
class PostPolicy:
    def update(self, user, post) -> bool:
        # User can update a post only if they own it
        return user.id == post.user_id

    def delete(self, user, post) -> bool:
        return user.get_attribute("is_admin") or user.id == post.user_id
```

### Registering & Checking Policies
```python
from app.Models.Post import Post

# Register Policy mapping (usually inside AuthServiceProvider)
Gate.policy(Post, PostPolicy)

# Check policy permissions in a controller action
post = Post.find("post-uuid")
if not Gate.check("update", user, post):
    return self.json({"message": "Forbidden"}, status=403)
```

---

## Sessions and CSRF

Sessions are signed with **HMAC-SHA256** using `APP_KEY`. A cookie that was
tampered with, or signed with a different key, is rejected rather than trusted.

> **Signed is not encrypted.** With `SESSION_DRIVER=cookie` the payload is
> base64-encoded JSON in the cookie — the client cannot *change* it, but can
> *read* it. Do not put secrets in the session under that driver. Use
> `SESSION_DRIVER=file`, which keeps the payload on the server and puts only a
> signed id in the cookie.

CSRF is verified on POST/PUT/PATCH/DELETE, via the `_token` field in the
request body or the `X-CSRF-TOKEN` header. A token in the query string is
ignored — it could be planted by a crafted cross-site link. Routes matching
`api/*` are exempt. A mismatch returns **419**.

```html
<form method="POST" action="/posts">
    @csrf
    <input name="title">
</form>
```

## Post-Quantum Cryptography (PQC)

Craft ships a hash-based one-time signature utility (`WOTS`, a Lamport-style
scheme over SHA-256) for signing tokens where post-quantum resistance matters.
Its security rests only on the preimage resistance of SHA-256, which holds
against quantum adversaries.

```python
from craft.facades import PQC
from craft.security.pqc import WOTS

seed = b"..."  # 32 random bytes — one seed must sign only ONE message
public_key = WOTS(seed).get_public_key()

token = PQC.sign_token(payload, secret_key, seed)
PQC.verify_token(token, secret_key, public_key)
```

How it works:

- Key material is derived deterministically from the seed; the public key is a
  single SHA-256 digest committing to all secret halves.
- Tokens are **hybrid**: `payload.hmac.wots_signature`. Verification checks
  **both** the classical HMAC-SHA256 (against `secret_key`) and the WOTS
  signature (against `public_key`) — either failing rejects the token. All
  comparisons are timing-safe (`hmac.compare_digest`).
- **One seed signs one message.** Reusing a seed for a second message reveals
  secret material and breaks the scheme — generate a fresh seed (and publish
  its public key) per token.

It is a standalone utility — **session cookies use HMAC-SHA256, not WOTS**. Wire
PQC in explicitly where you need it.

---

## Captcha Integration

A short alphanumeric challenge held in the session. Both calls take the request —
the code lives in the session, not in a token you pass around.

```python
from craft.facades import Captcha
from craft.http.response import Response

# In the GET handler: generate and render the challenge
code = Captcha.generate(request)
html = Captcha.get_obfuscated_html(code)

# In the POST handler: validate what the user typed
if not Captcha.validate(request, request.input("captcha")):
    return Response("Invalid Captcha Challenge", status=400)
```

The stored code is cleared on every validation attempt, whether or not it
succeeded — a captcha is single-use, otherwise one challenge can be brute-forced.

---

## Web Application Firewall (WAF) & Intrusion Detection (IDS)

Craft includes an integrated WAF and threat intelligence subsystem with IP reputation scoring, payload inspection, and automatic blacklisting.

### Protecting Routes via Middleware
Attach the `firewall` middleware alias to any route or group:

```python
Route.post("/api/v1/orders", [OrderController, "store"]) \
    .middleware("firewall", "api")
```

### Threat Signatures Detected in Real Time
The firewall inspects URIs, query strings, and payloads against regex threat patterns:
- **SQL Injection (SQLi)**: keywords (`UNION`, `SELECT`, `DROP`, `ALTER`), comment evasion (`--`, `/*`), and boolean tautologies (`'1'='1'`).
- **Cross-Site Scripting (XSS)**: script tags, `javascript:` pseudoprotocols, event handlers (`onerror=`, `onload=`), and cookie extraction attempts.
- **Path Traversal**: directory traversal tokens (`../`, `..\`) and sensitive OS file paths (`/etc/passwd`, `/windows/win.ini`).
- **Server-Side Request Forgery (SSRF)**: cloud metadata endpoints (`169.254.169.254`), loopback addresses, and internal network hostnames.

### Managing Firewall Rules Programmatically
Use the `Firewall` facade to manage reputation and rules:

```python
from craft.facades import Firewall

# Add trusted IP to whitelist (bypasses rate limits and inspection)
Firewall.whitelist_ip("192.168.1.50")

# Add malicious IP to blacklist (immediately returns 403 Forbidden)
Firewall.blacklist_ip("203.0.113.88", reason="Automated scanner detected")

# Check reputation score (threshold: 100 points = auto-blacklisted)
score = Firewall.get_reputation_score("203.0.113.88")
```

---

## Honeypot & Brute-Force Protection

Craft provides active deception defense and database-backed login cooldowns.

### Pre-Registered Attacker Honeypot
Commonly abused administrative usernames (`admin`, `root`, `administrator`, `postgres`, `superuser`, `operator`, `master`, `system`, etc.) are pre-configured as **honeypot traps**:
1. Any login attempt targeting these usernames is **blocked immediately**.
2. Never exposes real user models or query errors.
3. Records a `HONEYPOT` security event in `auth_audit_logs` and `security_events`.
4. Automatically assigns a **30-minute cooldown** to the attacking IP address.

### Brute-Force Cooldown (30 Minutes)
On normal user accounts, 5 consecutive failed login attempts activate a **30-minute cooldown** stored in PostgreSQL (`auth_cooldowns`). Subsequent attempts during cooldown are refused before credentials are checked. A successful login clears the failed attempt counter.

### Using Auth with Audit Tracking
Pass the client IP and User-Agent to `Auth.attempt()` to enable automatic auditing and cooldown enforcement:

```python
if Auth.attempt(
    {"email": email, "password": password},
    ip=request.ip(),
    user_agent=request.headers.get("user-agent"),
):
    return redirect(route="dashboard")
```

---

## API Token Hashing & Database SSL

### Hashed API Tokens
API tokens provided in `Authorization: Bearer <token>` are verified against SHA-256 hashes (`api_token_hash` or `api_token` column) with automatic backward compatibility. Raw tokens are never required to reside in plaintext in the database.

### PostgreSQL SSL Mode
Configure SSL enforcement in `config/database.py` or `.env` via `DB_SSLMODE`:

```python
# config/database.py
"pgsql": {
    "driver": "postgresql",
    "host": env("DB_HOST", "127.0.0.1"),
    "port": env("DB_PORT", 5432),
    "database": env("DB_DATABASE", "craft_db"),
    "username": env("DB_USERNAME", "craft"),
    "password": env("DB_PASSWORD", ""),
    "sslmode": env("DB_SSLMODE", "prefer"),  # 'require', 'verify-full', 'prefer'
}
```


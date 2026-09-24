# Authorization — RBAC, groups and ABAC

Craft ships a complete authorization system: **who** someone is (roles and
groups), **what** they may do (permissions), and **under which circumstances**
(attribute conditions on a grant). All three are data, so day-to-day access
management needs no code change; Gates and Policies remain available for the
decisions that genuinely belong in Python.

Two rules run through everything here:

- **Deny by default.** An ability nobody defined and no grant covers is a
  refusal. A failed authorization query is a refusal too — it decided nothing,
  and guessing "yes" is the one answer that cannot be corrected afterwards.
- **Authentication is not authorization.** `auth` proves who the visitor is.
  It never proves they may see the page. Every route under `/admin` must carry
  an authorizing alias as well, and `tests/test_admin_authorization.py` fails
  the build if one does not.

---

## How a permission reaches a user

Four paths, all resolved together by one query:

```
user → permission                  direct grant (permission_user)
user → role → permission           role_user + permission_role
user → group → role → permission   group_user + group_role + permission_role
user → group → permission          group_user + permission_group
```

**Grants add up; they never veto each other.** A user with a narrow grant and a
broad grant for the same permission gets the broad one.

### The tables

| Table | Purpose |
|---|---|
| `roles` | A named role: `admin`, `tenant-manager` |
| `permissions` | A named permission: `manage-users`, `publish-post` |
| `groups` | A named team: `content-team`, `support` |
| `role_user` | Which roles a user holds |
| `permission_role` | Which permissions a role grants |
| `group_user` | Who belongs to a group |
| `group_role` | Which roles a group grants to its members |
| `permission_group` | Permissions granted straight to a group |
| `permission_user` | A permission granted to one person |

Every grant table also has a nullable **`conditions`** column — that is the
ABAC half, below. `NULL` means unconditional.

### Why groups

Organisations grant access to a team, a department or a unit, not to one person
at a time. A group carries roles and/or permissions, and every member inherits
them, so onboarding is one membership row instead of a tour of every role that
team needs — and offboarding is one delete instead of an audit of five pivots.

### Why direct grants

One person occasionally needs one extra permission. Inventing a single-member
role for that is worse than recording it honestly, so `permission_user` exists.

---

## ABAC — conditions on a grant

A permission is often not absolute:

- *edit articles, **but only your own***
- *approve invoices, **but only under 10,000***
- *read patient records, **but only in your own department***

Those are attributes of the resource and of the acting user, not properties of
the role. Every grant may therefore carry a small JSON object, evaluated
against the record being acted upon:

```json
{"user_id": "@user.id"}
```

`@user.<attr>` is replaced with the acting user's attribute at check time, so
that condition reads "the record's `user_id` must equal the acting user's id" —
ownership, expressed as data.

### The vocabulary

A key with a plain value compares for equality. A key with a one-entry object
names an operator:

```json
{"status":      {"in": ["draft", "review"]}}
{"amount":      {"lte": 10000}}
{"department":  "@user.department"}
{"archived_at": {"is_null": true}}
```

| Operator | Meaning |
|---|---|
| *(none)* | equality |
| `eq`, `ne` | equal / not equal |
| `in`, `not_in` | membership in a list |
| `gt`, `gte`, `lt`, `lte` | ordering |
| `is_null` | the attribute is (or is not) null |
| `contains` | the attribute contains the value |

Every key must hold — the object is an AND. Anything more expressive belongs in
a Policy class, which is ordinary Python and can be tested.

### Three behaviours worth knowing

They are all deliberate, and each exists to fail safely:

1. **A conditional grant does not answer an unconditional question.**
   `has_permission("edit-articles")` is asked with no resource in hand, so a
   grant that says *only your own* returns `False` there. Use
   `can("edit-articles", article)` when you have the record. Answering `True`
   would hand out the unconditional version of a deliberately narrowed grant.
2. **A malformed condition denies**, and is logged as an error. A typo must
   never become an open grant.
3. **`{}` is not `NULL`.** An empty object means someone wrote something and
   meant it, so it denies rather than being read as "no conditions".

---

## Checking access

```python
from craft.facades import Auth, Gate

user = Auth.user()

user.has_role("admin")                    # direct or through a group
user.in_group("content-team")
user.has_permission("manage-users")       # unconditional grants only
user.can("edit-articles", article)        # evaluates conditions
user.permission_slugs()                   # everything reachable, for display
```

### The Gate

`Gate.allows(ability, user, resource)` resolves in order, first answer wins:

1. an ability closure registered with `Gate.define(...)`;
2. a method of the Policy registered for the resource's model;
3. the grant tables — the ability name doubles as a permission slug, and the
   resource is passed through so conditions are evaluated;
4. deny.

So a permission slug is a Gate ability for free, and `Gate.define`/a Policy
still overrides the data when a decision needs real code:

```python
Gate.authorize("edit-articles", user, article)   # raises AuthorizationException
```

### The Access facade — inspecting, not deciding

```python
from craft.facades import Access

Access.roles(user)          # ["admin"]
Access.groups(user)         # ["content-team"]
Access.permissions(user)    # every slug reachable, conditional included
Access.explain(user, "publish-post")
# [{"source": "group", "conditions": '{"user_id": "@user.id"}'}]
```

`explain()` answers "why can this person do that?" without reading five tables
by hand — the query an audit screen and an incident review both start from.

### Route middleware

```python
Route.get("/reports", [ReportController, "index"]).middleware("auth", "role:admin")
Route.get("/reports", [ReportController, "index"]).middleware("auth", "permission:view-reports")
Route.get("/support", [DeskController, "index"]).middleware("auth", "group:support")
```

Put `"auth"` first, so a guest is redirected to `/login` instead of getting a
403. An unknown alias raises **at boot**, not silently at request time.

> Route middleware asks without a resource, so a conditional grant does not
> satisfy it — the router cannot know which record the controller will load.
> Guard those in the controller with `Gate.authorize(ability, user, record)`
> once the record exists.

### In a view

```html
@if(auth() and auth().has_permission("manage-users"))
    <a href="/admin/groups">Manage groups</a>
@endif
```

---

## Managing access from the CLI

```bash
# Roles and permissions
python dev.py role list
python dev.py role create "Analyst" analyst
python dev.py permission create "Export Data" export-data
python dev.py role grant analyst export-data
python dev.py user assign-role someone@example.com analyst

# Groups
python dev.py group create "Support Team" support
python dev.py group add-user support someone@example.com
python dev.py group grant-role support analyst
python dev.py group grant support export-data

# Conditional (ABAC) grants
python dev.py group grant content-team publish-post --conditions '{"user_id": "@user.id"}'
python dev.py user grant someone@example.com approve-invoice --conditions '{"amount": {"lte": 10000}}'

# Who can do what, and why
python dev.py user access someone@example.com
```

`--conditions` is validated before anything is stored: a condition that cannot
be parsed is refused at the CLI, because at check time it would deny and look
like a grant that simply does not work.

The tables come with `craft make:admin`, which writes their migration. After
that, no migration is needed to add a role, a group or a permission: each is a
row.

## Admin UI

Generated by `craft make:admin`; a new project has none of these pages.

| Page | What it does |
|---|---|
| `/admin/roles` | Roles with their permissions; grant a permission to a role |
| `/admin/permissions` | The permission catalogue |
| `/admin/groups` | Groups with members, roles and direct permissions; create a group, add members, grant roles, grant permissions **with optional conditions** |

All of them require `auth` + `role:admin`. Granting access is itself an
authorized action, and these screens hand it out.

---

## What ships seeded

`migrate --seed` creates a working ladder rather than empty tables:

- **Roles** — `user` (basic) → `tenant-manager` (elevated: adds `manage-users`)
  → `admin` (everything).
- **A group** — `content-team`, granting the `user` role; the standard demo
  account is a member, so the group path is exercisable immediately.
- **One conditional grant** — the Content Team may `publish-post`, but only
  their own (`{"user_id": "@user.id"}`); administrators hold the same
  permission unconditionally. The feature is visible, not merely documented.

The three demo accounts are listed in [the README](../README.md#demo-accounts).

Check any of it with:

```bash
python dev.py user access user@craft.local
```

---

## Where this lives

| File | Role |
|---|---|
| `engine/auth/access.py` | `AccessResolver` — the single union query and every decision |
| `engine/auth/conditions.py` | The condition language, its operators and its parser |
| `engine/auth/gate.py` | `Gate` — closures, policies, then the grant tables, then deny |
| `engine/http/middleware.py` | `RequireRole`, `RequirePermission`, `RequireGroup` |
| `engine/auth/models.py` | `AuthorizableMixin` - `has_role`/`has_permission`/`can` for a user model, delegating to the resolver |
| `engine/auth/registry.py` | Resolves the project's `User`, `Role`, `Permission` and `Group` from `config/auth.py` |

Nothing outside `AccessResolver` re-implements "check the role table". A caller
that does gets one of the four paths wrong; keeping the union in one place
means adding a fifth path later changes one file.

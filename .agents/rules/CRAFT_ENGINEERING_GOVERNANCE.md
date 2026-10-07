# Engineering governance and code of conduct

**Target:** Craft Engine framework and ecosystem projects (Softpax and siblings).
**Status:** active and mandatory.
**Relation to the other files here:** `AGENTS.md` is the stack-agnostic contract
every project loads. This document is the Craft-scoped layer on top of it. Where
both speak, this one is more specific and wins; where they conflict, the conflict
is a bug in one of them and gets fixed, not worked around.

**Gates:** `python .agents/rules/lint_language.py` and
`python .agents/rules/lint_structure.py`. Both must exit 0.

---

## 1. Core philosophy and engineering principles

Every contributor, human or model, works to these:

1. **Explicit over implicit (PEP 20).** Magic behavior, hidden global state and
   undocumented monkey-patching are forbidden. Code is readable, explicit and
   self-documenting.
2. **Single responsibility.** Every class, module and function has exactly one
   reason to change.
3. **Convention over configuration.** Craft Engine's three-tier hierarchy is
   respected as written: **core engine** → **business modules** → **capability
   plugins**.
4. **Zero technical debt acceptance.** Temporary hacks, commented-out dead code
   and mixed-language identifiers are build failures, not notes for later.

---

## 2. Code quality standards and hard thresholds

Enforced by `lint_structure.py`. A contribution that breaks a threshold is
rejected; the fix is the code, never the threshold (`AGENTS.md` E5).

### File and function limits

| Layer | Cap | Responsibility |
|---|---|---|
| Controllers (thin HTTP layer) | **150 lines/file**, **15 lines/action** | Translate HTTP to a call and back |
| Domain services | **300 lines/file** | Business domain logic, exclusively |
| Repositories | **250 lines/file** | Raw SQL and query-builder interaction |
| Any function or method | **25 lines**, cyclomatic complexity **≤ 6** | One unit of work |

### Structural rules

- **No god controllers.** A controller handling several domain entities, or over
  its cap, is split into focused sub-controllers in the same change.
- **No SQL leakage.** Raw SQL, joins or direct database calls inside controllers
  or services are prohibited. `STRUCT-D`.
- **No inline markup.** Raw HTML or concatenated view strings inside Python are
  forbidden; layouts are `.html` templates rendered by the native Craft template
  engine. `STRUCT-E`.
- **Mandatory delegation to plugins.** Transversal algorithms — document
  validation, check digits, QR rendering, SEO slug sanitization — live in
  `app/plugins/` and are consumed through the IoC container, never copied into a
  module.

### Use the ecosystem, do not re-implement it

Craft Engine ships the boring parts. Re-writing them by hand is not neutral: it
loses the security, pagination and consistency the built-in already guarantees.

- **CRUD Builder.** Standard create, read, update and delete go through the CRUD
  Builder. Never hand-roll raw SQL or the boilerplate around it for a plain CRUD.
- **Forge.** Templates are rendered by Forge, with data passed as a dictionary or
  a Pydantic model. HTML, CSS and view strings never appear inside Python.
- **Dependency injection.** Services are resolved from the container. A route or
  controller never instantiates a service directly — that is what makes the code
  mockable in `pytest`.
- **Modules.** The codebase is organized into self-contained business modules
  (`auth_module`, `billing_module`), each with its own routes, services and
  models. No single god file.
- **Plugins.** A new cross-cutting capability — a payment gateway, a logging
  handler — is a plugin, removable without breaking the core. The core never
  swells to host it.

---

## 3. Linguistic governance and financial terminology

### English-only source

100% English codebase: class names, variables, method signatures, database
schemas, PEP 257 docstrings, `typing` annotations, commit messages and inline
comments, in standard American English. Enforced by `lint_language.py`
(LANG-A/B), and by LANG-F for committed documents.

Mixed-language identifiers are refactored to canonical domain English, never
left to "match the surrounding style": `_sem_dono` → `is_unassigned`,
`pega_dados` → `fetch_data`.

**Comments and docstrings are English; conversation is `pt-BR`.** These are the
two independent axes of `AGENTS.md`, and the split falls on "does it get
committed", not on "is it prose". A comment ships with the file, so it is
English; the explanation written next to a diff is read once, so it is `pt-BR`.
LANG-B rejects a Portuguese comment, and the fix is the comment.

### Brazilian financial and business terminology

The canonical mapping. These are the names; synonyms are drift.

| Domain term | Canonical English |
|---|---|
| Boleto bancário | **`bank_slip`** — `BankSlipService`, `generate_bank_slip`, `bank_slip_barcode` |
| PIX / transferência instantânea | `instant_payment` / `PIX` (the brand keeps its name) |
| Inscrição estadual (IE) | `state_registration` |
| Inscrição municipal (IM) | `municipal_registration` |
| Nota fiscal (NF-e / NFS-e) | `tax_invoice` / `electronic_invoice` |
| Razão social | `legal_name` / `corporate_name` |
| Nome fantasia | `trade_name` / `doing_business_as` |

`CPF`, `CNPJ`, `PIX` and `IBAN` stay as they are: legal and protocol proper
nouns, allowlisted in the language config.

---

## 4. Database-driven localization

1. **Zero hardcoded strings.** No customer-facing error message, UI label or
   notification text is hardcoded in Python, in a template, or in a flat static
   file (JSON, YAML, PO). Every one is a key resolved at runtime.
2. **Storage and hierarchy.** Locales live in the database:

   | Locale | Role |
   |---|---|
   | `en` | **Source.** Keys are authored here; the canonical key namespace |
   | `pt-BR` | **Default runtime locale** for end users and tenants |
   | `es` | Active alternative |

3. **Fallback chain:** tenant override → `pt-BR` → `en`.

Every key carries a row in all three locales in the change that creates it. A
key with fewer than three rows is unfinished — you translate, not a human
(`AGENTS.md` E7).

> **Locale codes.** This project uses the short forms `en` and `es`, not `en-US`
> and `es-ES`. The stack-agnostic `AGENTS.md` declares roles, not codes; the
> codes are declared here and are what the seeder writes. A legacy `pt` locale
> alongside `pt-BR` is drift and is collapsed into `pt-BR`, not maintained.

---

## 5. Writing the code — less is more

- **Guard clauses.** Validate edge cases at the top and return or raise
  immediately. Deep `if/else` nesting is a refactor, not a style.
- **Brevity.** Prefer comprehensions, generators and built-ins (`sum`, `map`,
  `filter`, `any`) over a verbose loop that rebuilds them.
- **One thing per function.** The hard cap is 25 lines (15 in a controller
  action) and `lint_structure.py` rejects past it — but the design target is
  **15–20**. A function pushing the cap is already asking to be split, with the
  extracted helpers prefixed `_`.
- **Immutability.** Never mutate an input argument. Return a new object.

---

## 6. Debuggability and robustness — fail fast

- **Strict typing.** Type hints on 100% of signatures: every parameter, every
  return. `STRUCT-H`.
- **Fail fast.** Validate inputs immediately and raise a specific exception
  (`ValueError`, `TypeError`, a `DomainException`) rather than returning a
  generic error string for a caller to interpret.
- **No blanket catches.** Bare `except:` and `except Exception:` are forbidden —
  they swallow what they cannot name. Catch the exception you can actually
  handle. `STRUCT-G`.
- **Contextual logging.** An error log carries the entity id, the user or tenant
  id, and the original exception message. A log line that cannot locate the
  failure is noise.

---

## 7. Testing and documentation

- **Docstrings.** Google-style on every public class and function — summary
  line, `Args:`, `Returns:`, `Raises:` where they apply. `STRUCT-I`.
- **Testability.** Inject dependencies instead of reaching for global state;
  code that cannot be mocked cannot be tested.
- **Test suggestions.** When a feature lands, name the one or two critical
  `pytest` cases it needs. Naming them is not writing them — write them when the
  work is a feature, not a sketch.

---

## 8. Working agreement

- **Architecture before business logic.** For anything beyond a local fix,
  confirm the architecture — modules, services, plugin boundaries, data shape —
  before writing the domain code. A confirmed shape is cheap; a rewritten module
  is not.
- **Output.** Code, plus a brief `pt-BR` explanation. Not a tour of the code
  already on screen.
- **Scope is still scope.** This agreement gates *design*, never *volume*. It is
  never grounds to deliver a subset of what was asked (`AGENTS.md` E1–E7).

---

## 9. Technology stack boundaries

- **Backend runtime:** 100% pure Python 3.10+, on Craft Engine architecture.
- **Typing and linting:** strict static typing (`mypy`-compliant) and PEP 8.
- **Frontend layer:** vanilla or vendored static `.js` and `.css` only. **Zero
  TypeScript**, **zero Node build pipelines**. `STRUCT-F`.
- **Multi-tenant safety:** every module and plugin is stateless and thread-safe,
  isolating tenant data at the query and service layers.

---

## 10. Definition of done

- [ ] `python .agents/rules/lint_language.py` exits 0
- [ ] `python .agents/rules/lint_structure.py` exits 0
- [ ] **Line caps:** no controller over 150 lines, no service over 300
- [ ] **Layer purity:** zero queries in controllers or services, zero markup in Python
- [ ] **Ecosystem:** CRUD through the CRUD Builder, views through Forge, services
      through the container — nothing hand-rolled that the engine already ships
- [ ] **Plugin isolation:** shared utility logic lives in `app/plugins/`
- [ ] **Typing:** every parameter and return annotated, `mypy` clean
- [ ] **Robustness:** no bare or broad `except`; errors logged with entity/user id
- [ ] **Docstrings:** Google-style on every public class and function
- [ ] **Language:** 100% English identifiers, docstrings and comments
- [ ] **Terminology:** boletos map to `bank_slip`, per the table in §3
- [ ] **i18n:** every message is a database-backed key with `en`, `pt-BR`, `es`
- [ ] **Tests:** unit and integration tests in `pytest`, all passing
- [ ] **Scope:** nothing deferred for cost, volume or tedium (`AGENTS.md` E1–E7)

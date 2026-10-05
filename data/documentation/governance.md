# Engineering Governance & Code of Conduct

Target: Craft Engine Framework & Ecosystem Projects (e.g., Softpax)
Status: Active & Mandatory

---

## 1. Core Philosophy & Engineering Principles

Every contributor (human or AI agent) must adhere to these foundational principles:

1. **Explicit Over Implicit (Zen of Python / PEP 20):** Magic behaviors, hidden global states, and undocumented monkey-patching are strictly forbidden. Code must be readable, explicit, and self-documenting.
2. **Single Responsibility Principle (SRP):** Every class, module, and function must have exactly one reason to change.
3. **Convention Over Configuration (Craft Engine Standard):** Strictly adhere to Craft Engine's three-tier hierarchy: **Core Engine** → **Business Modules** → **Capability Plugins**.
4. **Zero Technical Debt Acceptance:** Temporary hacks, commented-out dead code, and Portunglês ("salada de frutas") are treated as critical build failures.

---

## 2. Code Quality Standards & Hard Thresholds

Any contribution violating these thresholds will be automatically rejected:

### File & Function Limits
- **Controllers (Thin HTTP Layer):** Maximum **150 lines per file**. Actions must not exceed **15 lines**.
- **Domain Services:** Maximum **300 lines per file**. Handle business domain logic exclusively.
- **Repositories:** Maximum **250 lines per file**. Isolate raw SQL and query builder interactions.
- **Functions & Methods:** Maximum **25 lines per method**. Cyclomatic complexity must remain $\le 6$.

### Structural Rules
- **No Monolithic Controllers:** "God Controllers" handling multiple domain entities or exceeding line caps must be immediately refactored into focused sub-controllers.
- **No SQL Leakage:** Raw SQL, query joins, or direct database operations inside controllers or services are strictly prohibited.
- **No Inline HTML/Layouts:** Writing raw HTML or concatenating view strings inside Python controllers is forbidden. All layouts must use `.html` templates rendered via the native Craft Template Engine.
- **Mandatory Delegation to Plugins:** Transversal algorithms (e.g., document validation, mathematical check digits, QR code rendering, SEO slug sanitization) must live in a plugin extension under `app/plugins/<slug>/` and be consumed through the internal proxy, events or filters - never imported by another extension ([extensions.md](extensions.md)).

---

## 3. Linguistic Governance & Financial Standards

### English-Only Source Code
- **100% English Codebase:** All class names, variable names, method signatures, database schemas, docstrings (PEP 257), type annotations (`typing`), git commit messages, and inline comments must be written in standard American English.
- **Zero Portunglês / Colloquialisms:** Refactor informal or mixed-language identifiers to canonical domain English (e.g., replace `_sem_dono` with `is_unassigned`, `pega_dados` with `fetch_data`).

### Brazilian Financial & Business Terminology
Standardize all Brazilian financial terms into official domain English:
- *Boleto Bancário* → **`bank_slip`** (e.g., `BankSlipService`, `generate_bank_slip`, `bank_slip_barcode`)
- *PIX / Transferência Instantânea* → `Instant Payment` / `PIX`
- *Inscrição Estadual (IE)* → `State Registration`
- *Inscrição Municipal (IM)* → `Municipal Registration`
- *Nota Fiscal (NF-e/NFS-e)* → `Tax Invoice` / `Electronic Invoice`
- *Razão Social* → `Legal Name` / `Corporate Name`
- *Nome Fantasia* → `Trade Name` / `Doing Business As (DBA)`

---

## 4. Database-Driven Localization (i18n) Governance

1. **Zero Hardcoded Strings:** No customer-facing error messages, UI labels, or notification texts may be hardcoded in Python files, templates, or flat static files (JSON/YAML/PO).
2. **Database Storage & Hierarchy:**
   - **`en` (English):** System source and canonical translation key namespace.
   - **`pt-BR` (Brazilian Portuguese):** Default runtime locale for end users and tenants.
   - **`es` (Spanish):** Active alternative locale.
   - **Fallback Rule:** `Tenant Override` → `pt-BR` → `en` (Master Source).

---

## 5. Technology Stack Boundaries

- **Backend Runtime:** 100% pure Python (3.10+) built strictly on the Craft Engine architecture.
- **Typing & Linting:** Strict static typing (`typing` / `mypy` compliant) and PEP 8 formatting.
- **Frontend Layer:** Vanilla or vendor static `.js` and `.css` assets only. **Zero TypeScript (`.ts`)** and **zero Node.js build pipelines**.
- **Multi-Tenant Safety:** All modules and plugins must be stateless and thread-safe, strictly isolating tenant data at the query and service layers.

---

## 6. Definition of Done (DoD) & Pull Request Checklist

A task, refactoring, or feature is only complete when all items pass:

- [ ] **Line Cap Compliance:** No controller exceeds 150 lines; no service exceeds 300 lines.
- [ ] **Layer Purity:** Zero database queries inside controllers/services; zero HTML inside Python files.
- [ ] **Plugin Isolation:** Shared utility logic is encapsulated inside `app/plugins/`.
- [ ] **Language Standard:** 100% English identifiers, docstrings, and comments.
- [ ] **Financial Terminology:** Brazilian boletos are strictly mapped to `bank_slip`.
- [ ] **i18n Compliance:** All messages use database-backed localization keys.
- [ ] **Automated Tests:** Comprehensive unit and integration tests written in `pytest` with 100% passing status.

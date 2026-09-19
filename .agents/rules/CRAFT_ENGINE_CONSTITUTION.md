# Craft Engine Framework Constitution (MSR Standard)
Target: Craft Engine Framework (`msrjson/craftengine`) & Ecosystem Applications (e.g., Softpax)

When writing, scaffolding, or refactoring code, AI agents and developers are strictly prohibited from generating monolithic files, mixed-language identifiers, or procedural scripts. You MUST enforce the native architectural primitives of Craft Engine: **Business Modules**, **Capability Plugins**, **IoC/DI Container**, and the **Native Template Engine**.

---

## 1. MANDATORY ARCHITECTURAL TAXONOMY

In a clean Craft Engine workspace, `app/modules/` and `app/plugins/` start **clean and empty**. AI agents build project features from scratch into these directories according to the architectural tiers below (working examples are available under `documentation/examples/`):

```text
craft_project/
├── app/
│   ├── modules/                       # TIER 2: BUSINESS DOMAINS (Created by developer / agent)
│   │   ├── <business_domain>/         # Example: cms, billing, clinic, inventory...

│   │   │   ├── module.py              # Lifecycle: IoC bindings & route registration
│   │   │   ├── routes.py              # HTTP endpoint definitions
│   │   │   ├── controllers/           # Thin HTTP handlers (Max 150 lines per file)
│   │   │   │   ├── post_controller.py
│   │   │   │   ├── page_controller.py
│   │   │   │   └── media_controller.py
│   │   │   ├── services/              # Domain business rules & state transitions
│   │   │   │   ├── post_service.py
│   │   │   │   ├── page_service.py
│   │   │   │   └── media_service.py
│   │   │   ├── repositories/          # Isolated database queries & ORM interaction
│   │   │   │   ├── post_repository.py
│   │   │   │   ├── page_repository.py
│   │   │   │   └── media_repository.py
│   │   │   ├── schemas/               # Request/Response DTOs & typed dataclasses
│   │   │   └── templates/             # Isolated HTML views managed by Craft Template Engine
│   │   │
│   │   └── billing/                   # Billing Business Domain (Bank Slips, Invoices)
│   │       ├── module.py
│   │       ├── routes.py
│   │       ├── controllers/
│   │       ├── services/
│   │       └── repositories/
│   │
│   └── plugins/                       # TIER 3: CAPABILITY PLUGINS (Stateless & Transversal)
│       ├── brazil_validator/          # Zero-dependency Document Validator (CPF, CNPJ, IE, RG)
│       │   ├── plugin.py              # Plugin IoC provider & container registration
│       │   ├── engine.py              # Pure algorithms (Modulo 10/11, Alphanumeric CNPJ)
│       │   └── schemas.py             # Validation Result DTOs
│       ├── qrcode_generator/          # QR Code Rendering Utility (PIX, URL payloads)
│       ├── seo_optimizer/             # Meta tag, permalink & slug utility
│       └── storage_adapter/           # S3/Local file persistence capability
```

---

## 2. STRUCTURAL MANDATES

### Tier 1: Core Framework (`engine/`)
- Core HTTP kernel, ORM, Facades, Migration Engine, Container, and CLI toolchain.
- Standard application developers do NOT mutate `engine/` unless contributing to core framework capabilities.

### Tier 2: Business Modules (`app/modules/<module_name>/`)
- Business domain logic (CMS, Billing, CRM, Identity) MUST live in `app/modules/`.
- Every module MUST expose `module.py` with `register(app)` (IoC bindings) and `boot(app)` (route mounting & runtime events).
- Controllers MUST remain thin transport handlers (< 150 lines per file, 5-15 lines per action). No raw SQL, domain business logic, or HTML string building in controllers.
- Views MUST reside in `app/modules/<module_name>/templates/` rendered via Craft Engine's native Template Engine.

### Tier 3: Capability Plugins (`app/plugins/<plugin_name>/`)
- Transversal, stateless utilities (validators, QR generators, SEO analyzers) MUST live in `app/plugins/`.
- Every plugin MUST expose `plugin.py` declaring `PLUGIN` descriptor dict and `register(app)` binding the capability into the IoC container.
- Zero tenant or business state permitted in plugins.

---

## 3. LINGUISTIC & DOMAIN STANDARDS
- **100% English Codebase**: Identifiers, docstrings, comments, class and method names must be written in standard American English.
- **Financial Terminology**: Standardize Brazilian boleto to `bank_slip` across schemas, services, and endpoints.
- **Localization (i18n)**: User-facing text must be queried from database translation tables (`en` source, `pt-BR` default runtime). Zero hardcoded UI strings in Python.
- **Pure Python 3.14+**: 100% backend Python 3.14+ execution. Zero Node.js or TypeScript build pipelines.

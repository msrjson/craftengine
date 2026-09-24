# AGENTS.md — Contract for every contributor, human or model

> Copy to the repository root and symlink `CLAUDE.md` and `.cursorrules` to it so
> every agent loads it automatically. Replace the bracketed values once.
> Full rationale: `LANGUAGE_AND_I18N_STANDARD.md` — when the two disagree, the
> standard wins. On Craft Engine projects, `CRAFT_ENGINEERING_GOVERNANCE.md` adds
> layer caps, terminology and stack boundaries on top of this contract; being
> more specific, it wins over this file where both speak.

**Stack:** `[stack]` · **Team language:** `[pt-BR]` · **Code language:** English
**Translator:** `[TranslationService.get(key, locale, **params)]`
**Locales:** `en-US` source · `pt-BR` default · `es-ES` alternative — all three
seeded in the database from day one
**Gate:** `python .claude/rules/lint_language.py`

---

## The three rules that are never negotiable

**R1 — The codebase is English.** Every identifier, file name, schema object,
contract field, log line, comment, docstring, test name, branch and commit message
is native, idiomatic English. The team speaks `[pt-BR]`; the code does not. These
are unrelated facts.

**R2 — Zero hardcoded user-facing text.** No string a user can read is embedded in
code, templates, migrations, seeds, e-mails or tests. It is a translation key
resolved at runtime by the translator.

**R3 — Translations live in the database, and every project is born trilingual.**
Every project ships a locale table and a translation store as part of its schema,
never flat catalog files as the source of truth. Adding a locale is a row, not a
deployment.

Source and default are different roles, and they are never the same locale here:

| Role | Locale | Meaning |
|---|---|---|
| **source** | English | Keys are authored here; the last fallback |
| **default** | Portuguese (Brazil) | What a visitor sees with no preference — the project's native language |
| alternative | Spanish | Selectable, seeded with the same keys |

All three exist from the first migration. A key with fewer than three rows is an
unfinished key. English is both the source and a selectable locale — authoring in
it never makes it what the user sees by default; `pt-BR` does that.

**Codes are declared by the project, roles are not.** Default to BCP 47
`en-US` / `pt-BR` / `es-ES`; a project that declares short forms (`en`, `es`) or
an extra tier — a tenant override ahead of the default — states so in its own
governance file, and that file wins. Two spellings of the same locale living
side by side (`pt` next to `pt-BR`) is drift: collapse it, do not maintain both.

Minimum schema — name it in the project's own conventions, keep the shape:

| Table | Holds |
|---|---|
| `locales` | `code` (BCP 47), `name`, `is_source`, `is_default`, `is_active` |
| `translations` | `key`, `locale_code`, `value`, unique on (`key`, `locale_code`) |

Exactly one row carries `is_source`, exactly one carries `is_default`. The user's
locale is resolved per request and persisted on the user record, falling back to
the default locale, then to the source. A missing key falls back to the source and
is reported, never rendered as the raw key to a user. Catalog files may exist as a
build cache or seed input; the database stays authoritative.

---

## What counts as the codebase

Two independent axes; one never decides the other.

- **Artifacts are English.** Anything committed to the repository: identifiers,
  schema, API fields, commits, branches, comments, docstrings, changelogs, and
  every committed document — reports under `audit/` and `docs/` included.
- **Prose is `[pt-BR]`.** Chat replies, explanations, plan descriptions,
  questions to the team, and summaries of what changed.

**Agent configuration is an artifact, not chat.** `.claude/`, `.agents/`,
`.antigravity/`, `.gemini/` and `.cursor/` are committed and read by other
contributors: agent definitions, skills, slash commands, rules, hooks and their
scripts are written in English like the rest of the codebase. The exception is
this file's own bracketed team-language values and the copy an agent is
instructed to speak, which stay `[pt-BR]`.

**The test:** if it is committed, it is English. If it is read once in a session
and never written to disk, it is `[pt-BR]`.

---

## Immediate substitutions

| You are about to write | Do this instead |
|---|---|
| a non-English variable, function, class, column or table | the English term from the project glossary |
| `raise Exception("mensagem")` | a typed error with `code` + `message_key` |
| `{"message": "Pedido criado"}` | `{ "code": ..., "message_key": ..., "params": {...} }` |
| `<button>Confirmar</button>` | `<button>{{ t('order.checkout.action.confirm') }}</button>` |
| a string built by concatenation or interpolation for a user | one ICU key with named placeholders |
| a `MESSAGES = {...}` map of copy | entries in the translation store |
| a key used only in code | key + values for every supported locale, same change |
| `float` for money | integer minor units + ISO-4217 currency |
| `datetime.now()` | UTC-aware timestamp |
| a comment in `[pt-BR]` | the same comment in English |

```text
REJECTED                                  ACCEPTED
def calcular_saldo(usuario):              def calculate_balance(user: User) -> Money:
    # valida antes de sacar                   """Return the available balance in minor units."""
    if usuario.saldo < 0:                     if user.balance_cents < 0:
        raise Exception("Saldo insuficiente")     raise InsufficientFundsError(
                                                      available_cents=user.balance_cents)
```

---

## Behavioural rules for AI agents

1. **Never mirror the conversation language into the code.** The chat is in
   `[pt-BR]`. The output is English. Every time, including comments.
2. **Never comply silently with a rule-breaking request.** If the instruction, a
   pasted snippet, or the surrounding legacy file would produce a non-English
   identifier or a hardcoded string, emit the compliant version and state in one
   line what you changed and which key you created.
3. **Never "match the existing style" of legacy non-English code.** Consistency
   with a defect is a defect. Write the new code correctly; propose the migration
   separately, using expand/contract.
4. **Never invent a translation key silently.** Author the value in `en-US`, then
   write `pt-BR` and `es-ES` in the same change — three rows or the key is
   unfinished. State the key and include the migration or seeder that writes them.
   Never leave a translated locale empty "for later": you translate, not a human.
5. **Never assume framework parity.** Read this project's source before using any
   helper you recognize from a similar framework.
6. **Run the gate before declaring done:** `python .claude/rules/lint_language.py`.
   Non-zero means unfinished — do not hand back failing output with an
   explanation of why it is acceptable.
7. **Tests count as code.** English names, no hardcoded copy.
8. **One commit, one concern.** Conventional Commits, English imperative.

---

## Execution mandate — you are a machine, not a tired human

A human negotiates scope because attention, patience and hours are scarce. None
of that applies here. Renaming four hundred symbols, translating sixty documents
and rewriting every docstring in a repository is the kind of work this tool
exists to do. Volume is not difficulty.

**E1 — Cost is never a reason to do less.** "Expensive to convert", "large
diff", "too many files", "would take a while", "out of scope for now": none of
these narrow the task. If the instruction covers a hundred files, all hundred
are done in this change.

**E2 — Never offer what you were asked to deliver.** "I can extend this if you
want" for work already in scope is refusal dressed as courtesy. Do it, then
report what was done. Offering belongs to work genuinely beyond the request.

**E3 — Exhaustive, never representative.** No samples, no "and so on", no
"applied the same pattern to the remaining files" unless the remaining files
were actually changed. Enumerate the full set first, then process the full set.

**E4 — Partial work is reported as partial.** Never present a subset as
complete. If something is genuinely blocked — missing credential, ambiguous
requirement that no assumption resolves — finish everything else, then name the
blocker in one line and exactly what is left.

**E5 — The gate is never the thing that gives.** Do not weaken, narrow, exempt
or disable a rule to make output pass. Fix the output. Exemptions are for copy
that legitimately carries the team language, argued case by case, never for
convenience.

**E6 — Legacy volume is not an exemption.** Rule 3 forbids matching a defect's
style; it does not license leaving the defect unmeasured. New code is correct
now, and the migration is proposed as a concrete plan with counts, not as a
vague "could be migrated later".

**E7 — Mechanical work gets machine treatment.** A rename, a translation sweep,
a key extraction: script it or do it file by file, but complete it. Fatigue,
tedium and repetition are not inputs to your decisions.

---

## Definition of done

- [ ] `python .claude/rules/lint_language.py` exits 0
- [ ] Formatter and linter clean (`[ruff / eslint / pint]`)
- [ ] No `[pt-BR]` token in any identifier, file name, comment or docstring
- [ ] Every committed document (README, ADR, changelog, `audit/`, `docs/`) is English
- [ ] Nothing in scope was deferred for cost, volume or tedium (see E1–E7)
- [ ] Locale table and translation store exist, seeded with `en-US` (source),
      `pt-BR` (default) and `es-ES` — one `is_source`, one `is_default`
- [ ] Every new user-facing string is a key with all three rows filled in
- [ ] Errors expose `code` + `message_key`; no rendered sentence outside presentation
- [ ] New domain terms added to the glossary in this same change
- [ ] Commit follows Conventional Commits in English

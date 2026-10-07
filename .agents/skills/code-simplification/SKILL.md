---
name: code-simplification
description: Reduces complexity in working code while preserving its exact behavior. Use when refactoring for clarity, when code works but is harder to read, maintain or extend than it should be, or when a review flags accumulated complexity.
---

# Code Simplification

## Overview

Simplify code by reducing complexity while keeping behavior identical. The goal is not fewer
lines — it is code that is faster to read, understand, change and debug. Every simplification
passes one test: "Would a new team member understand this faster than the original?"

In Craft Engine, simplification also has a hard floor set by governance: the result must still
respect the layer caps, keep SQL out of controllers and services, keep markup out of Python, keep
user-facing text in translation keys, and pass both lint gates. A "simpler" version that breaks
one of those is not simpler — it is a regression.

## When to Use

- A feature works and its tests pass, but the implementation is heavier than it needs to be
- A review flagged readability or complexity (see `.claude/skills/code-review-and-quality/SKILL.md`)
- You meet deep nesting, long functions or unclear names
- `python .claude/rules/lint_structure.py` reports a function over 25 lines, complexity over 6,
  or a file over its layer cap
- Code was written under time pressure and shows it
- Related logic is scattered across files and should be consolidated
- A merge introduced duplication or inconsistency

**When NOT to use:**

- The code is already clean and readable — do not simplify for its own sake
- You do not yet understand what the code does — comprehend first
- The code is performance-critical and the "simpler" version is measurably slower
- The module is about to be rewritten — simplifying throwaway code wastes effort

## The Five Principles

### 1. Preserve Behavior Exactly

Change how the code expresses itself, never what it does. Inputs, outputs, side effects, raised
exception types, error codes, `message_key` values, emitted events, queued jobs, database writes
and their ordering all stay identical. If you are unsure a simplification preserves behavior,
do not make it.

```text
ASK BEFORE EVERY CHANGE:
-> Does it produce the same output for every input?
-> Does it raise the same exception type, code and message_key?
-> Does it keep the same side effects (writes, events, jobs, cache) in the same order?
-> Do all existing tests still pass without modification?
```

### 2. Follow Project Conventions

Simplifying means making code more consistent with this codebase, not importing outside
preferences. Before simplifying:

```text
1. Read .claude/rules/ (AGENTS.md, CRAFT_ENGINEERING_GOVERNANCE.md) and the project CLAUDE.md
2. Study how neighboring code handles the same pattern
3. Match the project's style for:
   - Import ordering (ruff's isort rules)
   - Layer placement (controller -> service -> repository, plugins for cross-cutting logic)
   - Naming conventions (English, glossary terms, snake_case functions, PascalCase classes)
   - Error handling (typed errors with code + message_key, no broad except)
   - Type annotation depth (every parameter and return annotated)
   - Docstring style (Google style on public classes and functions)
```

Simplification that breaks project consistency is not simplification — it is churn.

### 3. Prefer Clarity Over Cleverness

Explicit code beats compact code when the compact form needs a mental pause to parse.

```python
# UNCLEAR: chained conditional expressions
status_key = "order.status.new" if order.is_new else "order.status.updated" if order.is_updated else "order.status.archived" if order.is_archived else "order.status.active"


# CLEAR: a named function with guard clauses
def status_key_for(order: Order) -> str:
    """Return the translation key describing the order's status.

    Args:
        order: The order to describe.

    Returns:
        A translation key resolved by the presentation layer.
    """
    if order.is_new:
        return "order.status.new"
    if order.is_updated:
        return "order.status.updated"
    if order.is_archived:
        return "order.status.archived"
    return "order.status.active"
```

```python
# UNCLEAR: a reduce with inline dictionary rebuilding
from functools import reduce

counts = reduce(
    lambda acc, item: {**acc, item.sku: acc.get(item.sku, 0) + 1}, items, {}
)

# CLEAR: the standard library already names this operation
from collections import Counter

counts = Counter(item.sku for item in items)
```

### 4. Maintain Balance

Simplification has a failure mode: over-simplification. Watch for these traps:

- **Inlining too aggressively** — removing a helper that gave a concept a name makes the call
  site harder to read
- **Combining unrelated logic** — two simple functions merged into one complex function is not
  simpler, and it will trip the 25-line and complexity caps
- **Removing "unnecessary" abstraction** — some abstractions exist for testability (a service
  resolved from the container so `pytest` can swap it) or for layer purity (a repository that
  holds the SQL), not for complexity
- **Collapsing layers** — moving a query from the repository "back" into the service to save a
  file is a governance violation (`STRUCT-D`), not a simplification
- **Optimizing for line count** — fewer lines is not the goal; faster comprehension is

### 5. Scope to What Changed

Default to simplifying recently modified code. Avoid drive-by refactors of unrelated code
unless the scope was explicitly widened. Unscoped simplification makes diffs noisy and risks
regressions in code nobody meant to touch.

## The Simplification Process

### Step 1: Understand Before Touching (Chesterton's Fence)

Before changing or removing anything, understand why it exists. If you find a fence across a
road and do not know why it is there, do not tear it down. First learn the reason, then decide
whether it still applies.

```text
BEFORE SIMPLIFYING, ANSWER:
- What is this code's responsibility, and which layer owns it?
- What calls it? What does it call? (routes/web.py, routes/api.py, listeners, jobs, scheduler)
- What are the edge cases and error paths?
- Which pytest tests define the expected behavior?
- Why might it have been written this way? (Performance? A driver quirk between PostgreSQL
  and SQLite? Thread safety? A historical reason?)
- Check git blame and CHANGELOG.md: what was the original context?
```

If you cannot answer these, you are not ready to simplify. Read more context first.

### Step 2: Identify Simplification Opportunities

Scan for these patterns — each is a concrete signal, not a vague smell.

**Structural complexity:**

| Pattern | Signal | Simplification |
| --- | --- | --- |
| Deep nesting (3+ levels) | Hard-to-follow control flow | Guard clauses or extracted helpers |
| Long functions (over 25 lines; 15 in a controller action) | Several responsibilities, fails `STRUCT-B` | Split into focused functions, helpers prefixed `_` |
| Complexity over 6 | Fails `STRUCT-C` | Lookup table, dispatcher, or extracted predicates |
| Chained conditional expressions | Needs a mental stack to parse | `if` chain, `match` statement, or a mapping |
| Boolean parameter flags | `export(orders, True, False, True)` | Keyword-only arguments, an `Enum`, or separate functions |
| Repeated conditionals | Same `if` check in several places | A well-named predicate function or model property |
| Oversized controller or service | Fails `STRUCT-A` | Focused sub-controllers or services, one concern each |

**Naming and readability:**

| Pattern | Signal | Simplification |
| --- | --- | --- |
| Generic names | `data`, `result`, `temp`, `val`, `item` | Name the content: `customer_profile`, `validation_errors` |
| Abbreviated names | `usr`, `cfg`, `btn`, `evt` | Full words unless universal (`id`, `url`, `api`) |
| Non-English names | identifiers from the team's language | The canonical English term from the glossary |
| Misleading names | A `get_` function that also writes | Rename to the actual behavior |
| Comments explaining "what" | `# increment counter` above `count += 1` | Delete the comment — the code says it |
| Comments explaining "why" | `# Retry: the gateway drops idle connections after 30s` | Keep — it carries intent the code cannot |

**Redundancy:**

| Pattern | Signal | Simplification |
| --- | --- | --- |
| Duplicated logic | The same 5+ lines in several places | Extract a shared function; if cross-cutting, a plugin in `app/plugins/` |
| Dead code | Unreachable branches, unused variables, commented-out blocks | Remove after confirming it is truly dead |
| Unnecessary abstractions | A wrapper that adds nothing | Inline it and call the underlying function |
| Over-engineered patterns | A factory for one product, a strategy with one strategy | The direct approach |
| Redundant type casts | `cast()` to a type already inferred | Remove the cast |
| Hand-rolled engine features | Custom pagination, CRUD boilerplate, ad-hoc validation | `paginate()`, `python dev.py make:crud`, a `FormRequest` |
| Reinvented standard library | Manual counting, grouping, deduplication | `collections.Counter`, `itertools`, `set`, comprehensions |

### Step 3: Apply Changes Incrementally

Make one simplification at a time and run the tests after each. **Submit refactoring separately
from feature or bug-fix work.** A change that refactors and adds a feature is two changes.

```text
FOR EACH SIMPLIFICATION:
1. Make the change
2. Run python -m pytest tests (or the focused test module, then the full suite at the end)
3. Pass -> commit, or continue to the next simplification
4. Fail -> revert and reconsider
```

Do not batch several simplifications into one untested change. When something breaks you need
to know which one caused it.

**The Rule of 500:** if a refactor would touch more than 500 lines, invest in automation — an AST
transform, a `ruff --fix` rule, a scripted rename — instead of editing by hand. Manual edits at
that scale are error-prone and exhausting to review. Scale is a reason to automate, never a
reason to stop partway.

### Step 4: Verify the Result

After all simplifications, step back and judge the whole:

```text
COMPARE BEFORE AND AFTER:
- Is the simplified version genuinely easier to understand?
- Did it introduce any pattern inconsistent with the codebase?
- Does it still respect the layer caps and layer purity?
- Is the diff clean and reviewable?
- Would a teammate approve this change?
```

If the "simplified" version is harder to understand or review, revert. Not every attempt
succeeds.

## Language-Specific Guidance

### Python

```python
# SIMPLIFY: verbose dictionary building
# Before
names_by_id = {}
for customer in customers:
    names_by_id[customer.id] = customer.legal_name
# After
names_by_id = {customer.id: customer.legal_name for customer in customers}


# SIMPLIFY: verbose conditional assignment
# Before
if customer.trade_name:
    display_name = customer.trade_name
else:
    display_name = customer.legal_name
# After
display_name = customer.trade_name or customer.legal_name


# SIMPLIFY: manual list building
# Before
active_customers = []
for customer in customers:
    if customer.is_active:
        active_customers.append(customer)
# After
active_customers = [customer for customer in customers if customer.is_active]


# SIMPLIFY: redundant boolean return
# Before
def is_valid_reference(reference: str) -> bool:
    if 0 < len(reference) < 100:
        return True
    return False
# After
def is_valid_reference(reference: str) -> bool:
    return 0 < len(reference) < 100


# SIMPLIFY: nested conditionals -> guard clauses
# Before
def capture_payment(payment: Payment | None) -> Receipt:
    if payment is not None:
        if payment.is_valid():
            if payment.is_authorized():
                return gateway.capture(payment)
            else:
                raise PaymentNotAuthorizedError(payment_id=payment.id)
        else:
            raise InvalidPaymentError(payment_id=payment.id)
    else:
        raise PaymentMissingError()
# After
def capture_payment(payment: Payment | None) -> Receipt:
    if payment is None:
        raise PaymentMissingError()
    if not payment.is_valid():
        raise InvalidPaymentError(payment_id=payment.id)
    if not payment.is_authorized():
        raise PaymentNotAuthorizedError(payment_id=payment.id)
    return gateway.capture(payment)
```

Each error above is a typed `DomainError` subclass carrying `code` and `message_key`; the
simplification keeps the same classes and the same order of checks, so callers and tests see
identical behavior.

```python
# SIMPLIFY: a long if/elif dispatch that fails the complexity cap
# Before
def fee_cents_for(method: str, amount_cents: int) -> int:
    if method == "bank_slip":
        return 350
    elif method == "instant_payment":
        return 0
    elif method == "credit_card":
        return amount_cents * 3 // 100
    elif method == "debit_card":
        return amount_cents * 15 // 1000
    else:
        raise UnsupportedPaymentMethodError(method=method)


# After: a typed lookup keeps complexity flat as methods are added
from collections.abc import Callable

FEE_RULES: dict[str, Callable[[int], int]] = {
    "bank_slip": lambda _amount_cents: 350,
    "instant_payment": lambda _amount_cents: 0,
    "credit_card": lambda amount_cents: amount_cents * 3 // 100,
    "debit_card": lambda amount_cents: amount_cents * 15 // 1000,
}


def fee_cents_for(method: str, amount_cents: int) -> int:
    rule = FEE_RULES.get(method)
    if rule is None:
        raise UnsupportedPaymentMethodError(method=method)
    return rule(amount_cents)
```

Docstrings are omitted from the before/after snippets for brevity; the real functions keep their
Google-style docstrings.

### Controllers and services

```python
# SIMPLIFY: a controller action doing a service's job
# Before — query, business rule and response in one action (fails STRUCT-B and STRUCT-D)
async def store(self, request: StoreOrderRequest) -> Response:
    rows = DB.select("SELECT * FROM carts WHERE user_id = ?", [request.user().id])
    ...  # 30 lines of pricing, stock checks and persistence


# After — the action translates HTTP; the injected service decides
class OrderController(Controller):
    """Handle order HTTP endpoints."""

    def __init__(self, orders: OrderService) -> None:
        self.orders = orders

    async def store(self, request: StoreOrderRequest) -> Response:
        """Place an order from the authenticated user's cart."""
        order = self.orders.place_from_cart(request.user(), request.validated())
        return OrderResource.make(order).response(status=201)
```

The HTTP kernel builds controllers through the container (`app.make`), which autowires
constructor parameters from their type hints — so the service arrives injected and a test can
bind a double in its place. Match the shape of the project's generated files
(`python dev.py make:controller`, `python dev.py make:resource`) for imports and base classes.

### Forge templates

```html
<!-- SIMPLIFY: duplicated branches that differ only in a key and a class -->
<!-- Before -->
{% if user.is_admin %}
  <span class="badge badge--admin">{{ __('user.role.admin') }}</span>
{% else %}
  <span class="badge badge--member">{{ __('user.role.member') }}</span>
{% endif %}

<!-- After -->
{% set role = 'admin' if user.is_admin else 'member' %}
<span class="badge badge--{{ role }}">{{ __('user.role.' ~ role) }}</span>
```

A repeated block used across several views belongs in an included partial under
`resources/views`, not copied. Never "simplify" a template by replacing a translation key with a
literal sentence.

### Vanilla JavaScript

```javascript
// SIMPLIFY: manual array building
// Before
const visibleRows = [];
for (const row of rows) {
  if (!row.hidden) {
    visibleRows.push(row);
  }
}
// After
const visibleRows = rows.filter((row) => !row.hidden);

// SIMPLIFY: one listener per button -> one delegated listener
// Before
document.querySelectorAll('[data-action="remove"]').forEach((button) => {
  button.addEventListener('click', onRemove);
});
// After
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action="remove"]');
  if (button) onRemove(event);
});
```

Frontend code stays vanilla or vendored static `.js`. A simplification that introduces a
TypeScript file, an npm package or a build step fails `STRUCT-F` and is rejected.

## Common Rationalizations

| Rationalization | Reality |
| --- | --- |
| "It's working, no need to touch it" | Working code that is hard to read is hard to fix when it breaks. Simplifying now saves time on every future change. |
| "Fewer lines is always simpler" | A one-line chained conditional is not simpler than a five-line `if` chain. Simplicity is comprehension speed. |
| "I'll quickly simplify this unrelated code too" | Unscoped simplification makes noisy diffs and risks regressions in code you did not mean to change. |
| "The types make it self-documenting" | Types document structure, not intent. A well-named function explains *why* better than a signature explains *what*. |
| "This abstraction might be useful later" | Do not preserve speculative abstractions. If nothing uses it now, remove it and re-add it when needed. |
| "The original author must have had a reason" | Maybe — check git blame and apply Chesterton's Fence. Often accumulated complexity is just residue of iteration under pressure. |
| "I'll refactor while adding this feature" | Separate refactoring from feature work. Mixed changes are harder to review, revert and understand. |
| "Putting the query back in the service removes a file" | It removes a file and adds a `STRUCT-D` violation. Layer purity is not negotiable. |
| "Inlining the literal is simpler than a key" | Hardcoded user-facing text fails the language gate. The key stays. |

## Red Flags

- A simplification that needs test changes to pass (you probably changed behavior)
- "Simplified" code that is longer and harder to follow than the original
- Renames that follow personal preference instead of project conventions and the glossary
- Error handling removed or widened (`except Exception:`) "to make it cleaner"
- A different exception type, `code` or `message_key` coming out of the same input
- Simplifying code you do not fully understand
- Many simplifications batched into one large, hard-to-review commit
- Refactoring outside the task's scope without being asked
- SQL moved into a controller or service, or markup moved into Python
- A service instantiated directly instead of resolved from the container, "to avoid indirection"
- Type hints or docstrings dropped to shorten a function under its cap

## Verification

After a simplification pass:

- [ ] All existing tests pass without modification (`python -m pytest tests`)
- [ ] `ruff check engine` passes with no new warnings
- [ ] `python .claude/rules/lint_structure.py` exits 0 — no layer cap, complexity, SQL or markup
      violation introduced
- [ ] `python .claude/rules/lint_language.py` exits 0 — names and comments English, no literal copy
- [ ] Each simplification is a reviewable, incremental change
- [ ] The diff is clean — no unrelated changes mixed in
- [ ] Simplified code follows project conventions (checked against `.claude/rules/`)
- [ ] No error handling was removed or weakened; exception types, codes and keys are unchanged
- [ ] No dead code left behind (unused imports, unreachable branches, orphaned templates or keys)
- [ ] A `CHANGELOG.md` entry under `## [Unreleased]` (`Changed`) records the refactor
- [ ] A teammate or `.claude/agents/code-reviewer.md` would approve it as a net improvement

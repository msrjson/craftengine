---
name: frontend-ui-engineering
description: Builds production-quality, accessible, responsive server-rendered UI with Forge templates and vanilla JS/CSS, with every state handled and every string a translation key. Use when building or changing pages, partials, forms or interactive widgets, implementing layouts, meeting WCAG 2.1 AA, or when the output must look deliberately designed rather than generated.
---

# Frontend UI Engineering

## Overview

Build user interfaces that are accessible, fast and visually deliberate. The goal is UI that looks
like a design-aware engineer built it, not like it was generated: real adherence to the project's
design tokens, correct semantics and accessibility, considered interaction patterns, and none of
the generic "generated" aesthetic.

In Craft Engine projects the frontend is server-rendered **Forge templates** in
`resources/views/` (`.forge.py` files) plus **vanilla or vendored static `.js` and `.css`** under
`public/`. There is no TypeScript, no Node build pipeline and no package manager for the frontend.
Every string a user can read is a translation key resolved with `__()`, stored in the database
with rows for `en` (source), `pt-BR` (default) and `es`.

## When to Use

- Building new pages, layouts or partials
- Changing an existing user-facing interface
- Implementing responsive layouts
- Adding interactivity with vanilla JS (progressive enhancement)
- Building or changing forms
- Fixing visual, UX or accessibility issues

## Page Architecture

### File Structure

Keep everything that belongs to one screen together, and keep the layers apart:

```
app/Http/Controllers/Tasks/TaskController.py   # prepares the view data, no markup
resources/views/tasks/
  index.forge.py            # the page: extends the layout, composes partials
  _list.forge.py            # the list partial
  _item.forge.py            # one row
  _empty.forge.py           # empty state
  _form.forge.py            # create/edit form shared by both pages
public/assets/js/tasks.js   # progressive enhancement for this screen only
public/assets/css/craft-components.css   # shared component styles (tokens, not raw values)
tests/test_task_pages.py    # feature tests for rendering and states
```

HTML never lives in Python. Controllers pass a dictionary to `self.view()`; templates render it.

### Composition Patterns

**Prefer composition over configuration.** A page extends a layout and fills sections; repeated
blocks are partials pulled in with `@include`, not one giant template driven by flags:

```html
{# resources/views/tasks/index.forge.py #}
@extends("layouts.app")

@section("title", __("task.index.title"))

@section("content")
<section aria-labelledby="tasks-heading">
    <h1 id="tasks-heading">{{ __("task.index.heading") }}</h1>
    @include("tasks._list")
</section>
@endsection
```

```html
{# Avoid: one template configured by a pile of switches #}
@include("partials.card")   {# with card_title, card_variant, card_padding, card_body_html ... #}
```

**Keep partials focused.** One partial, one job:

```html
{# resources/views/tasks/_item.forge.py #}
<li class="task-item">
    <form action="/tasks/{{ task.id }}/toggle" method="POST" class="task-item__toggle">
        @csrf
        @method("PATCH")
        <input type="checkbox" id="task-{{ task.id }}" name="is_complete"
               @if(task.is_complete) checked @endif
               data-autosubmit>
        <label for="task-{{ task.id }}" class="@if(task.is_complete) task-item__title--done @endif">
            {{ task.title }}
        </label>
    </form>
    @can("delete", task)
    <form action="/tasks/{{ task.id }}" method="POST">
        @csrf
        @method("DELETE")
        <button type="submit" class="button button--ghost"
                aria-label="{{ __('task.item.action.archive_named', title=task.title) }}">
            <svg aria-hidden="true" focusable="false" class="icon"><use href="#icon-archive"></use></svg>
        </button>
    </form>
    @endcan
</li>
```

**Separate data preparation from presentation.** The controller (thin, container-resolved
service) decides what state the page is in; the template only renders it:

```python
class TaskController(Controller):
    """Thin HTTP layer for the task pages."""

    def __init__(self, tasks: TaskService) -> None:
        self.tasks = tasks

    def index(self, request: Request) -> Response:
        """Render one page of the current user's tasks."""
        page = self.tasks.list_tasks(ListTasksParams.from_query(request.all()))
        return self.view("tasks.index", {"tasks": page, "pagination": page.pagination})
```

```html
{# resources/views/tasks/_list.forge.py #}
@if(tasks|length == 0)
    @include("tasks._empty")
@else
    <ul class="task-list" aria-label="{{ __('task.list.label') }}">
        @foreach(tasks as task)
            @include("tasks._item")
        @endforeach
    </ul>
@endif
```

## State Management

**Choose the simplest place for state that works:**

```
Server-rendered page state   -> what the controller passes to the template (the default)
URL query parameters         -> filters, sorting, pagination, anything shareable or bookmarkable
Form state + old input       -> redisplay after validation failure with old('field') and @error
Session flash                -> one-time confirmations after a redirect
DOM state (data-* attributes)-> small widget state owned by one element
Module-scoped JS variable    -> transient state of one enhanced widget on one page
Server via fetch + JSON API  -> partial refreshes; the server stays the source of truth
```

**Do not rebuild a client-side application.** If a screen needs a client-side store shared across
many widgets, first ask whether a full page render or a partial fragment would do. Most screens
are a form, a list and a few enhancements.

## Design System Adherence

### Avoid the Generated Aesthetic

Generated UI has recognizable defaults. Avoid all of them:

| Generated default | Why it is a problem | Production quality |
|---|---|---|
| Purple/indigo everything | "Safe" default palettes make every app look identical | Use the project's actual color tokens |
| Excessive gradients | Visual noise that clashes with most design systems | Flat or subtle gradients the design system specifies |
| Maximum rounding everywhere | Ignores the hierarchy of corner radii in real designs | Radii from the design tokens |
| Generic hero sections | Template layout disconnected from content and user need | Content-first layouts |
| Placeholder filler copy | Hides length, wrapping and overflow problems | Realistic content in all three locales |
| Oversized padding everywhere | Destroys hierarchy and wastes space | A consistent spacing scale |
| Stock card grids | Ignores information priority and scanning patterns | Purpose-driven layouts |
| Shadow-heavy design | Competes with content, slows low-end devices | Subtle or no shadows unless specified |

Test layouts with the longest locale, not the shortest: Portuguese and Spanish strings are often
20 to 35 percent longer than English, and a button that fits `Save` may break on the translation.

### Spacing and Layout

Use the spacing scale defined as CSS custom properties. Never invent values:

```css
/* public/assets/css/craft-theme.css defines the tokens once */
:root {
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
    --space-4: 1rem;
    --space-6: 1.5rem;
}

/* Good */ .task-item { padding: var(--space-4); gap: var(--space-3); }
/* Bad  */ .task-item { padding: 13px; margin-top: 2.3rem; }
```

### Typography

Respect the type hierarchy:

```
h1    -> page title (one per page)
h2    -> section title
h3    -> subsection title
p     -> default text
small -> secondary or helper text
```

Do not skip heading levels. Do not use heading styles for non-heading content, and do not use
headings just to get a larger font.

### Color

- Use semantic tokens (`--color-text-primary`, `--color-surface`, `--color-border-default`), not raw hex values in component rules
- Ensure sufficient contrast: 4.5:1 for normal text, 3:1 for large text and UI components
- Never rely on color alone to convey information; pair it with text, an icon or a pattern

## Accessibility (WCAG 2.1 AA)

Every page and widget meets these standards. Full checklist:
`.claude/references/accessibility-checklist.md`.

### Keyboard Navigation

```html
<!-- Every interactive element must be keyboard accessible -->
<button type="button" data-action="expand">{{ __("task.item.action.expand") }}</button>  <!-- focusable by default -->
<div data-action="expand">{{ __("task.item.action.expand") }}</div>                       <!-- wrong: not focusable -->
```

If a native element is truly impossible, a custom control needs `role`, `tabindex="0"` and both
keys: Enter activates on keydown, Space activates on keyup (and its default scroll is prevented on
keydown). Prefer `<button>`; it gives you all of this for free.

```js
// public/assets/js/disclosure.js: only for a control that cannot be a <button>.
function makeActivatable(element, onActivate) {
  element.addEventListener("keydown", (event) => {
    if (event.key === "Enter") onActivate(event);
    if (event.key === " ") event.preventDefault();
  });
  element.addEventListener("keyup", (event) => {
    if (event.key === " ") onActivate(event);
  });
  element.addEventListener("click", onActivate);
}
```

### Labels and ARIA

```html
<!-- Label controls that have no visible text -->
<button type="button" aria-label="{{ __('dialog.action.close') }}">
    <svg aria-hidden="true" focusable="false" class="icon"><use href="#icon-close"></use></svg>
</button>

<!-- Label form inputs with a visible label -->
<label for="email">{{ __("account.profile.field.email") }}</label>
<input id="email" name="email" type="email" autocomplete="email" value="{{ old('email', '') }}">

<!-- aria-label only when no visible label exists -->
<input type="search" name="q" aria-label="{{ __('task.index.search_label') }}">
```

Translated ARIA labels are copy like any other: keys, three rows each.

### Forms, Errors and Security Directives

Every state-changing form carries `@csrf`; public forms also carry `@honeypot` and `@antispam`.
Errors are tied to their field and announced:

```html
<form action="/tasks" method="POST" novalidate>
    @csrf
    @honeypot
    @antispam

    <div class="field">
        <label for="title">{{ __("task.form.field.title") }}
            <span class="field__required">{{ __("form.field.required_marker") }}</span>
        </label>
        <input id="title" name="title" type="text" required
               value="{{ old('title', '') }}"
               aria-describedby="title-error"
               @error('title') aria-invalid="true" @enderror>
        @error('title')
            <p id="title-error" class="field__error">
                <svg aria-hidden="true" focusable="false" class="icon"><use href="#icon-alert"></use></svg>
                {{ message }}
            </p>
        @enderror
    </div>

    <button type="submit" class="button button--primary">{{ __("task.form.action.create") }}</button>
</form>
```

Validation messages rendered by `@error` must themselves come from translation keys; a
FormRequest's `messages()` returns keys resolved through `__()`, never literal sentences.

### Focus Management

Move focus when content changes, trap it inside modal dialogs, and return it on close. The native
`<dialog>` element with `showModal()` provides the focus trap, `Escape` handling and inertness of
the page behind it:

```html
<button type="button" data-dialog-open="confirm-archive">{{ __("task.item.action.archive") }}</button>

<dialog id="confirm-archive" aria-labelledby="confirm-archive-title">
    <h2 id="confirm-archive-title">{{ __("task.archive.confirm.title") }}</h2>
    <p>{{ __("task.archive.confirm.body") }}</p>
    <form method="dialog">
        <button value="cancel" data-dialog-initial-focus>{{ __("action.cancel") }}</button>
        <button value="confirm">{{ __("task.archive.confirm.action") }}</button>
    </form>
</dialog>
```

```js
// public/assets/js/dialogs.js
document.querySelectorAll("[data-dialog-open]").forEach((trigger) => {
  const dialog = document.getElementById(trigger.dataset.dialogOpen);
  trigger.addEventListener("click", () => {
    dialog.showModal();
    dialog.querySelector("[data-dialog-initial-focus]")?.focus();
  });
  dialog.addEventListener("close", () => trigger.focus());
});
```

### Meaningful Empty, Loading and Error States

Never show a blank screen. Every list, table and data widget has three explicit states besides
"has data": loading, empty and error.

```html
{# resources/views/tasks/_empty.forge.py #}
<div class="empty-state" role="status">
    <svg aria-hidden="true" focusable="false" class="empty-state__icon"><use href="#icon-tasks"></use></svg>
    <h2 class="empty-state__title">{{ __("task.list.empty.title") }}</h2>
    <p class="empty-state__body">{{ __("task.list.empty.body") }}</p>
    <a class="button button--primary" href="/tasks/create">{{ __("task.list.empty.action") }}</a>
</div>
```

For a widget that loads through the JSON API, render all state copy on the server into the markup
so the script never contains a sentence:

```html
<section class="task-feed" data-task-feed data-source="/api/v1/tasks?per_page=20"
         aria-labelledby="feed-title">
    <h2 id="feed-title">{{ __("task.feed.title") }}</h2>

    <div data-state="loading" aria-busy="true">
        <span class="visually-hidden">{{ __("task.feed.loading") }}</span>
        <div class="skeleton-row"></div><div class="skeleton-row"></div><div class="skeleton-row"></div>
    </div>

    <div data-state="empty" hidden role="status">{{ __("task.feed.empty") }}</div>

    <div data-state="error" hidden role="alert">
        <p>{{ __("task.feed.error") }}</p>
        <button type="button" data-retry>{{ __("action.retry") }}</button>
    </div>

    <ul data-state="ready" hidden class="task-list"></ul>
</section>
```

```js
// public/assets/js/task-feed.js
function showState(root, name) {
  root.querySelectorAll("[data-state]").forEach((el) => {
    el.hidden = el.dataset.state !== name;
  });
}

function renderTasks(list, tasks) {
  list.replaceChildren(
    ...tasks.map((task) => {
      const item = document.createElement("li");
      item.textContent = task.title; // textContent, never innerHTML, for server data
      return item;
    })
  );
}

async function loadFeed(root) {
  showState(root, "loading");
  try {
    const response = await fetch(root.dataset.source, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const { data } = await response.json();
    if (data.length === 0) return showState(root, "empty");
    renderTasks(root.querySelector('[data-state="ready"]'), data);
    showState(root, "ready");
  } catch (error) {
    console.error("task_feed_load_failed", { source: root.dataset.source, error });
    showState(root, "error");
  }
}

document.querySelectorAll("[data-task-feed]").forEach((root) => {
  root.querySelector("[data-retry]").addEventListener("click", () => loadFeed(root));
  loadFeed(root);
});
```

When the API returns an error envelope, the script shows the error state whose copy was already
translated on the server; if it must show a specific message, it looks the `message_key` up in the
locale bundle the page was given, never in a hardcoded map.

## Responsive Design

Design for small screens first, then add columns as space allows, with plain CSS:

```css
/* Mobile: single column */
.task-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-4);
}

/* Small screens and up: two columns */
@media (min-width: 40rem) {
    .task-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* Large screens: three columns */
@media (min-width: 64rem) {
    .task-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
```

Test at 320px, 768px, 1024px and 1440px, and at 200% text zoom.

## Loading and Transitions

- **Skeletons for content, spinners only for short actions.** A skeleton keeps the layout stable
  and avoids layout shift when data arrives.
- **Disable the submit button while a form posts** and re-enable it on failure, so a double click
  does not create two records (and back it with server-side idempotency; see the
  `api-and-interface-design` skill, `.claude/skills/api-and-interface-design/SKILL.md`).
- **Optimistic updates with rollback.** Apply the change to the DOM immediately, send the request,
  and restore the previous state if it fails:

```js
// public/assets/js/task-toggle.js
document.querySelectorAll("[data-task-toggle]").forEach((checkbox) => {
  checkbox.addEventListener("change", async () => {
    const previous = !checkbox.checked;
    const item = checkbox.closest(".task-item");
    item.classList.toggle("task-item--done", checkbox.checked);
    try {
      const response = await fetch(checkbox.dataset.url, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRF-TOKEN": document.querySelector('meta[name="csrf-token"]').content,
        },
        body: JSON.stringify({ is_complete: checkbox.checked }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      checkbox.checked = previous;
      item.classList.toggle("task-item--done", previous);
      document.getElementById("task-status").textContent = checkbox.dataset.errorMessage;
    }
  });
});
```

The CSRF middleware accepts the token from the `_token` body field or the `X-CSRF-TOKEN` header;
expose it once in the layout with `<meta name="csrf-token" content="{{ csrf_token() }}">`. The
error message comes from a `data-error-message="{{ __('task.toggle.error') }}"` attribute rendered
on the server, and `#task-status` is an `aria-live="polite"` region.

- **Respect reduced motion.** Wrap non-essential animation in
  `@media (prefers-reduced-motion: no-preference)`.

## Progressive Enhancement

Pages work without JavaScript: links navigate, forms post and redirect. Scripts enhance a working
page (autosubmit, inline toggles, dialogs, partial refresh). Load them with `defer` through
`asset()` so the version query string busts caches on release:

```html
<script src="{{ asset('assets/js/task-feed.js') }}" defer></script>
```

Vendored third-party scripts are committed under `public/` with their license, pinned to a version,
and never fetched from a CDN at runtime.

## See Also

For detailed accessibility requirements and testing tools, see
`.claude/references/accessibility-checklist.md`. For browser verification, see the
`browser-testing-with-devtools` skill (`.claude/skills/browser-testing-with-devtools/SKILL.md`).
For load and rendering budgets, see `.claude/references/performance-checklist.md`.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Accessibility is a nice-to-have" | It is a legal requirement in many jurisdictions and an engineering quality standard. |
| "We'll make it responsive later" | Retrofitting responsive layout costs several times more than building it in. |
| "The design isn't final, so I'll skip styling" | Use the design tokens. Unstyled UI gives reviewers a broken first impression. |
| "This is just a prototype" | Prototypes become production. Build the foundation right. |
| "The generated look is fine for now" | It signals low quality. Use the project's design system from the start. |
| "I'll translate the labels at the end" | Hardcoded copy is a gate failure now, and extracting it later is error-prone. Keys from the first line. |
| "A small build step would make this easier" | The stack is vanilla or vendored static assets. No Node pipeline, no TypeScript. |
| "The empty state will never happen" | Every new user, every new tenant and every filter with no match sees it. |

## Red Flags

- Templates over roughly 200 lines instead of being split into partials
- HTML strings built in Python, or `innerHTML` fed with server data
- Hardcoded user-facing text in templates, scripts, `aria-label`s or `alt` attributes
- Inline styles or arbitrary pixel values instead of tokens
- Missing loading, error or empty states
- State-changing forms without `@csrf`; public forms without `@honeypot` / `@antispam`
- No keyboard testing
- Color as the only indicator of state
- Generated look (purple gradients, oversized cards, stock layouts)
- `package.json`, TypeScript files or a bundler appearing in the repository

## Verification

After building UI:

- [ ] Pages render without errors in the server log or browser console
- [ ] All interactive elements are keyboard accessible (Tab through the whole page)
- [ ] A screen reader conveys the page's content, structure and state changes
- [ ] Responsive at 320px, 768px, 1024px and 1440px, and usable at 200% zoom
- [ ] Loading, error and empty states are all implemented and tested
- [ ] Follows the design tokens (spacing, color, typography)
- [ ] Every user-facing string is a key with `en`, `pt-BR` and `es` rows, checked with the longest locale
- [ ] Forms carry `@csrf` (and `@honeypot` / `@antispam` when public) and show field errors with `@error`
- [ ] No accessibility errors in Lighthouse or the Chrome DevTools accessibility tree
- [ ] Feature tests in `tests/` cover each rendered state
- [ ] `python .claude/rules/lint_language.py` and `python .claude/rules/lint_structure.py` exit 0

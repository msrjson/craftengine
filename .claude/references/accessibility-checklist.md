# Accessibility Checklist

Quick reference for WCAG 2.1 AA compliance in Craft Engine projects: Forge templates in
`resources/views/`, vanilla JS and CSS under `public/`. Use alongside the
`frontend-ui-engineering` skill (`.claude/skills/frontend-ui-engineering/SKILL.md`).

Every piece of text below that a user can read or hear, including `alt`, `aria-label`, `title`,
placeholder and live-region text, is a translation key resolved with `__()` and stored with rows for
`en`, `pt-BR` and `es`. Accessibility copy is copy.

## Table of Contents

- [Essential Checks](#essential-checks)
- [Common HTML Patterns](#common-html-patterns)
- [Testing Tools](#testing-tools)
- [Quick Reference: ARIA Live Regions](#quick-reference-aria-live-regions)
- [Common Anti-Patterns](#common-anti-patterns)

## Essential Checks

### Keyboard Navigation

- [ ] All interactive elements focusable via the Tab key
- [ ] Focus order follows the visual and logical order
- [ ] Focus is visible (an outline or ring on focused elements, never removed)
- [ ] Custom widgets have keyboard support (Enter to activate, Escape to close)
- [ ] No keyboard traps (the user can always Tab away from a component)
- [ ] Skip-to-content link at the top of the layout, visible at least on keyboard focus
- [ ] Modals trap focus while open and return focus to the trigger on close (native `<dialog>` with `showModal()`)

### Screen Readers

- [ ] All images have `alt` text (a key), or `alt=""` for decorative images
- [ ] All form inputs have associated labels (`<label for>` or `aria-label`)
- [ ] Buttons and links have descriptive text (not "click here")
- [ ] Icon-only buttons have `aria-label`, and the icon itself is `aria-hidden="true"`
- [ ] The page has one `<h1>` and headings do not skip levels
- [ ] Dynamic content changes are announced (`aria-live` regions)
- [ ] Tables have `<th>` headers with `scope`

### Visual

- [ ] Text contrast at least 4.5:1 (normal text) or 3:1 (large text, 18px+ or 14px+ bold)
- [ ] UI components and focus indicators at least 3:1 against the background
- [ ] Color is not the only way to convey information
- [ ] Text resizable to 200% without breaking layout or clipping translated strings
- [ ] No content flashes more than 3 times per second
- [ ] Non-essential motion respects `prefers-reduced-motion`

### Forms

- [ ] Every input has a visible label
- [ ] Required fields indicated by text or symbol with a text equivalent, not by color alone
- [ ] Error messages are specific, translated, and associated with the field (`aria-describedby`, `aria-invalid`)
- [ ] Error state visible by more than color (icon, text, border)
- [ ] Submission errors summarized at the top of the form, and the summary receives focus
- [ ] Known fields use `autocomplete` (for example `type="email" autocomplete="email"`)
- [ ] Previously entered values are restored after a failed submission (`old('field')`), so users do not retype
- [ ] Anti-spam fields (`@honeypot`, `@antispam`) are hidden from assistive technology and never receive focus

### Content

- [ ] Language declared on the root element and matching the resolved locale (`<html lang="{{ locale() }}">`)
- [ ] Parts in a different language marked with their own `lang` attribute
- [ ] The page has a descriptive, translated `<title>`
- [ ] Links are distinguishable from surrounding text by more than color
- [ ] Touch targets at least 44x44px on mobile
- [ ] Meaningful empty, loading and error states (never a blank screen)

## Common HTML Patterns

### Buttons vs. Links

```html
<!-- Use <button> for actions; in a Forge form, state changes post with @csrf -->
<form action="/tasks/{{ task.id }}" method="POST">
    @csrf
    @method("DELETE")
    <button type="submit">{{ __("task.item.action.archive") }}</button>
</form>

<!-- Use <a> for navigation -->
<a href="/tasks/{{ task.id }}">{{ __("task.item.action.view") }}</a>

<!-- NEVER use div or span as buttons -->
<div data-action="archive">{{ __("task.item.action.archive") }}</div>  <!-- BAD -->
```

### Form Labels

```html
<!-- Explicit label association -->
<label for="email">{{ __("account.profile.field.email") }}</label>
<input id="email" name="email" type="email" autocomplete="email" required>

<!-- Implicit wrapping -->
<label>
    {{ __("account.profile.field.email") }}
    <input name="email" type="email" autocomplete="email" required>
</label>

<!-- Hidden label (a visible label is preferred) -->
<input type="search" name="q" aria-label="{{ __('task.index.search_label') }}">
```

### Field Errors

```html
<label for="title">{{ __("task.form.field.title") }}</label>
<input id="title" name="title" type="text" required
       value="{{ old('title', '') }}"
       aria-describedby="title-error"
       @error('title') aria-invalid="true" @enderror>
@error('title')
    <p id="title-error" class="field__error">{{ message }}</p>
@enderror
```

### ARIA Roles

```html
<!-- Navigation landmarks, each with a distinct label -->
<nav aria-label="{{ __('layout.nav.main') }}">...</nav>
<nav aria-label="{{ __('layout.nav.footer') }}">...</nav>

<!-- Status messages -->
<div role="status" aria-live="polite">{{ __("task.save.succeeded") }}</div>

<!-- Alert messages -->
<div role="alert">{{ __("task.form.error.title_required") }}</div>

<!-- Modal dialogs (open with showModal() so focus is trapped) -->
<dialog aria-labelledby="dialog-title">
    <h2 id="dialog-title">{{ __("task.archive.confirm.title") }}</h2>
    ...
</dialog>

<!-- Loading states -->
<div aria-busy="true">
    <span class="visually-hidden">{{ __("task.list.loading") }}</span>
    <div class="skeleton-row"></div>
</div>
```

### Accessible Lists

```html
<ul aria-label="{{ __('task.list.label') }}">
    @foreach(tasks as task)
    <li>
        <input type="checkbox" id="task-{{ task.id }}" name="is_complete">
        <label for="task-{{ task.id }}">{{ task.title }}</label>
    </li>
    @endforeach
</ul>
```

When CSS removes list styling (`list-style: none`), some screen readers stop announcing the list;
add `role="list"` to the `<ul>` in that case.

### Skip Link

```html
<a class="skip-link" href="#main">{{ __("layout.skip_to_content") }}</a>
...
<main id="main" tabindex="-1">
    @yield("content")
</main>
```

```css
.skip-link {
    position: absolute;
    transform: translateY(-120%);
}

.skip-link:focus {
    transform: translateY(0);
}
```

## Testing Tools

```bash
# Automated audit in the browser
# Chrome DevTools -> Lighthouse -> Accessibility category
# Chrome DevTools -> Elements -> Accessibility pane (computed name, role, tree)
# Chrome DevTools -> Rendering -> Emulate vision deficiencies / prefers-reduced-motion

# Rendered-markup checks in the test suite
python -m pytest tests -k "accessibility or pages"

# Screen reader testing
# macOS: VoiceOver (Cmd + F5)
# Windows: NVDA (free) or JAWS
# Linux: Orca
```

Rendered-markup checks are cheap feature tests: request the page through the project's HTTP test
client and assert on the HTML, for example that every `<input>` has a matching `<label for>`, that
`<html lang>` matches the requested locale, and that no raw translation key (a string such as
`task.form.field.title`) leaked into the output because a row was missing. Pair them with a manual
keyboard pass and a screen reader pass for every new screen.

See the `browser-testing-with-devtools` skill
(`.claude/skills/browser-testing-with-devtools/SKILL.md`) for driving these checks in a live browser.

## Quick Reference: ARIA Live Regions

| Value | Behavior | Use For |
|-------|----------|---------|
| `aria-live="polite"` | Announced at the next pause | Status updates, saved confirmations |
| `aria-live="assertive"` | Announced immediately | Errors, time-sensitive alerts |
| `role="status"` | Same as `polite` | Status messages |
| `role="alert"` | Same as `assertive` | Error messages |

The live region must exist in the DOM before its text changes; inserting a new element that already
contains the message is often not announced. Render the empty region in the Forge template and set
its `textContent` from JS.

## Common Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `div` as button | Not focusable, no keyboard support | Use `<button>` |
| Missing `alt` text | Images invisible to screen readers | Add a descriptive translated `alt` |
| Hardcoded `aria-label` or `alt` in one language | Unusable for users of the other locales | A translation key with all three rows |
| Color-only states | Invisible to color-blind users | Add icons, text or patterns |
| Autoplaying media | Disorienting, cannot be stopped | Add controls, do not autoplay |
| Custom dropdown with no ARIA | Unusable by keyboard or screen reader | Use native `<select>` or a proper ARIA listbox |
| Removing focus outlines | Users cannot see where they are | Style outlines, do not remove them |
| Empty links or buttons | Announced as "link" or "button" with no name | Add text or `aria-label` |
| `tabindex` greater than 0 | Breaks the natural tab order | Use `tabindex="0"` or `-1` only |
| Errors shown only as a red border | Not perceivable without color, not announced | Text message tied with `aria-describedby`, `aria-invalid="true"` |
| `<html lang="en">` on every locale | Screen readers pronounce Portuguese or Spanish with English rules | `lang="{{ locale() }}"` |

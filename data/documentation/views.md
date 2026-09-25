# Views

Forge renders templates from `resources/views` using Jinja2 with Forge
directives. Templates live in `.forge.py` files.

## Rendering

```python
from craft.http.controller import Controller


class PostController(Controller):
    def index(self, request):
        return self.view("posts.index", {"posts": Post.all()})
```

View names use dot notation: `posts.index` resolves to
`resources/views/posts/index.forge.py`.

> Errors propagate. A missing template raises `TemplateNotFound`, an unknown
> directive raises `TemplateSyntaxError` naming it and its line, and with
> `APP_DEBUG` on an undefined variable raises `UndefinedError` when it is
> printed, iterated or has an attribute read (`{% if flash %}` on a missing
> name is still simply false). The exception handler turns each into a 500. Forge used to swallow every error and return a placeholder — a broken
> view looked like a working page.
>
> That legacy behaviour survives in one place: the standalone `view()` helper
> in `craft.support` still swallows rendering errors and returns a stub
> response. Use `self.view()` in controllers instead.

## Layouts

```html
<!-- resources/views/layouts/app.forge.py -->
<!doctype html>
<html>
<head><title>@yield("title")</title></head>
<body>
    @yield("content")
</body>
</html>
```

```html
<!-- resources/views/posts/index.forge.py -->
@extends("layouts.app")

@section("title", "Posts")

@section("content")
    <h1>{{ __('recent_posts') }}</h1>
@endsection
```

`@extends` and `@include` accept dot notation and resolve it to a path.

## Directives

| Directive | Compiles to |
|---|---|
| `@csrf` | Hidden `_token` input |
| `@method("PUT")` | Hidden `_method` input |
| `@auth` … `@endauth` | Renders only when signed in |
| `@guest` … `@endguest` | Renders only when signed out |
| `@can('ability', model)` … `@endcan` | Gate check |
| `@if(cond)` `@elseif(cond)` `@else` `@endif` | Conditional |
| `@foreach(items as item)` or `@foreach(item in items)` … `@endforeach` | Loop |
| `@extends("layouts.app")` | Template inheritance |
| `@section("name")` … `@endsection` | Named block |
| `@section("name", "value")` | Inline block |
| `@yield("name")` | Block placeholder |
| `@include("partials.nav")` | Include a template |

Directives are rewritten before Jinja compiles the template, so Jinja syntax
works alongside them. Anything else shaped like a directive - `@for`, `@push`,
`@isset`, `@include` with data - is refused with the list above rather than sent
to the browser as text. CSS at-rules such as `@media` and `@import` are left
alone.

## Forms and CSRF

Every state-changing form needs a token. `@csrf` emits it:

```html
<form method="POST" action="/posts">
    @csrf
    <input name="title" value="{{ old('title') }}">
    <button type="submit">Save</button>
</form>
```

Without it the request is rejected with **419**. See [Security](security.md).

HTML forms only support GET and POST. For other verbs:

```html
<form method="POST" action="/posts/1">
    @csrf
    @method("PUT")
</form>
```

## Helpers available in every template

| Helper | Returns |
|---|---|
| `csrf_token()` | The raw token |
| `csrf_field()` | The hidden input |
| `auth()` | The signed-in user, or `None` |
| `can(ability, *args)` | Gate check |
| `route(name, **params)` | URL for a named route |
| `config(key, default)` | Configuration value |
| `session(key, default)` | Session value |
| `old(key, default)` | Previously submitted input |
| `__(key, locale)` | Translation |

```html
@auth
    <p>{{ __('dashboard') }}, {{ auth().get_attribute('name') }}</p>
    <a href="{{ route('posts.index') }}">{{ __('recent_posts') }}</a>
@endauth
```

## Sharing data

Make a value available to every template:

```python
class AppServiceProvider(ServiceProvider):
    def boot(self):
        self.app.make("view").share("app_version", "1.0")
```

## Escaping

Autoescaping is on. `{{ value }}` escapes HTML:

```html
{{ "<script>alert(1)</script>" }}   →   &lt;script&gt;alert(1)&lt;/script&gt;
```

Render trusted HTML with `| safe`, and only when you control the source:

```html
{{ captcha_html | safe }}
```

## Checking a template exists

```python
forge = app.make("view")
if forge.exists("posts.index"):
    ...
```

# Validation

## Validator

```python
from craft.validation import Validator

validator = Validator(request.all(), {
    "name":     ["required", "string", "max:255"],
    "email":    "required|email|unique:users,email",
    "age":      ["nullable", "integer", "between:18,120"],
    "password": ["required", "min:8", "confirmed"],
})

if validator.fails():
    return self.json({"errors": validator.errors}, status=422)

data = validator.validated()
```

Rules are a list or a pipe-delimited string — the two are equivalent.

`validated()` returns only the fields you wrote rules for, and raises
`ValidationException` if validation failed. Extra input the client sent is
dropped, so nothing unvalidated reaches your model.

## How rules are applied

Only `required*` rules run against a field that is absent or empty. Everything
else is skipped, so an optional field left blank does not report a type error.

`nullable` makes an explicit `None` acceptable.

## Available rules

**Presence and Prohibitions**

| Rule | Passes when |
|---|---|
| `required` | Not `None`, `""`, `[]` or `{}` (zero passes) |
| `required_if:other,value` | Required only when `other` equals `value` |
| `required_with:a,b` | Required when any listed field is present |
| `required_without:a,b` | Required when any listed field is absent or empty |
| `required_without_all:a,b` | Required when all listed fields are absent or empty |
| `prohibited` | Must not be present or must be empty |
| `prohibited_if:other,value` | Prohibited when `other` equals `value` |
| `prohibited_unless:other,val` | Prohibited unless `other` equals `val` |
| `honeypot` | Trap field must be completely empty |
| `nullable` | Allows an empty value |

**Types and Structure**

| Rule | Passes when |
|---|---|
| `string` | Value is a string |
| `integer` | An int or a numeric string. **Booleans fail** — `bool` subclasses `int` in Python, and accepting `True` as an integer is a bug |
| `numeric` | int, float, or a numeric string |
| `boolean` | `True`, `False`, `0`, `1`, `"0"`, `"1"`, `"true"`, `"false"` |
| `array` | A list or tuple |
| `date` | A date/datetime, or an ISO-8601 string |
| `json` | Value is a valid JSON-encoded string |

**Formats, Networks, Text and Strings**

- `email`: Valid email address (standard RFC format, valid domain).
- `url`: Valid HTTP or HTTPS URL.
- `text`: Plain text only (strictly rejects raw HTML tags and script injection).
- `alpha_spaces`: Letters and whitespace only (supports all Unicode accents: á, é, ç, etc.).
- `no_html`: Rejects any HTML tags (`<...>`).
- `uuid`, `alpha`, `alpha_num`, `alpha_dash`, `regex:<pattern>`.
- `ip` (IPv4 or IPv6), `ipv4`, `ipv6`, `digits:n`, `digits_between:min,max`.
- `decimal:places`, `starts_with:a,b`, `ends_with:x,y`, `timezone`, `spam_free`.

**File Uploads and MIME Types**

| Rule | Passes when |
|---|---|
| `file` | Valid uploaded file object (`UploadFile`, dict with filename, or local path) |
| `image` | Valid image file (MIME starting with `image/` or extension in `jpg`, `png`, `gif`, `webp`, `svg`, `bmp`, `ico`) |
| `mimes:ext1,ext2,...` | File extension or MIME type matches allowed set (e.g. `mimes:pdf,docx,png`) |
| `max_file_size:kb` | File size does not exceed specified kilobytes (e.g. `max_file_size:2048` for 2MB) |
| `min_file_size:kb` | File size meets or exceeds specified kilobytes |

**Size** — counts characters for strings, items for collections, and compares
the value itself for numbers.

`min:n`, `max:n`, `between:min,max`, `size:n`.

When the field is also declared `integer` or `numeric`, a numeric string is
compared as a number: HTML form input `"25"` under
`["integer", "between:18,120"]` passes as the number 25, not as a 2-character
string.

**Sets and comparisons**

| Rule | Passes when |
|---|---|
| `in:a,b,c` | Value is one of the list |
| `not_in:a,b` | Value is not in the list |
| `same:other` | Matches another field |
| `different:other` | Differs from another field |
| `confirmed` | Matches `<field>_confirmation` |
| `accepted` | `True`, `1`, `"on"`, `"yes"`, `"true"` |

**Database**

```python
"email": ["unique:users,email"]                 # no such row exists
"email": ["unique:users,email,{id},id"]         # ignoring the current record
"role_id": ["exists:roles,id"]                  # the row must exist
```

If no database is reachable these rules skip rather than rejecting valid data.

An unknown rule name raises `ValueError` — a typo'd rule that silently does
nothing would leave a field looking validated when it is not.

## Results

```python
validator.passes()          # bool
validator.fails()           # bool
validator.errors            # {"email": ["Enter a valid email address."]}
validator.first_error()     # first message, any field
validator.first_error("email")
validator.error_messages()  # flat list
validator.validated()       # validated subset, or raises
```

## Custom messages

```python
Validator(data, {"name": ["required"]}, {"name": "Tell us your name."})
```

A `"field.rule"` key targets one rule; a bare `"field"` key covers every rule
on the field. The specific key wins:

```python
Validator(data, {"name": ["required", "max:50"]}, {
    "name.required": "Tell us your name.",
    "name.max": "Keep it under 50 characters.",
})
```

## FormRequest

Move rules and authorization next to the endpoint:

```python
# app/Http/Requests/StorePostRequest.py
from craft.validation import FormRequest


class StorePostRequest(FormRequest):
    def authorize(self) -> bool:
        return self.user() is not None

    def rules(self) -> dict:
        return {
            "title": ["required", "string", "max:255"],
            "body": ["required", "string"],
            "published": ["nullable", "boolean"],
        }

    def messages(self) -> dict:
        return {"title": "A title is required."}

    def prepare_for_validation(self, data: dict) -> dict:
        data = dict(data)
        if "title" in data:
            data["title"] = data["title"].strip()
        return data
```

```python
def store(self, request):
    data = StorePostRequest(request).validated()
    post = Post.create(data)
    return self.json(PostResource(post).to_array(), status=201)
```

`validated()` authorizes first — raising `AuthorizationException` (403) — then
validates, raising `ValidationException` (422). Both are rendered by the
exception handler.

Or declare it in the action's signature. The kernel builds it from the request
and runs `validated()` before the action is called, so the action cannot run on
input that failed the rules:

```python
def store(self, form: StorePostRequest):
    post = Post.create(form.validated())
    return self.json(PostResource(post).to_array(), status=201)
```

The injection follows the annotation, whatever the parameter is called:
`request: StorePostRequest` receives the form, not the raw request. Calling
`validated()` again returns the cached result without re-running the checks.

> `validated()` used to return the request body untouched, so every rule
> declared on a FormRequest was silently ignored. If you are upgrading, expect
> requests that previously slipped through to now be rejected.

Inspect without raising:

```python
form = StorePostRequest(request)
if form.fails():
    return self.view("posts.create", {"errors": form.errors})
```

## Views and Forge Directives

Display validation errors cleanly using `@error` and protect forms with `@honeypot`:

```html
<form method="POST" action="/posts">
    @csrf
    @honeypot

    <label for="title">Title</label>
    <input type="text" name="title" id="title" value="{{ old('title') }}">
    @error('title')
        <p class="text-danger">{{ message }}</p>
    @enderror

    <button type="submit">Submit</button>
</form>
```

When validation fails in a controller action, redirect back with errors and previous input:

```python
from craft.http.response import redirect

if validator.fails():
    return redirect.back(request).with_errors(validator).with_input(request.all())
```

## Localized messages

Rule messages are English by default. Translate them through the catalog:

```python
from craft.support import __

{"email": __("validation.email")}
```

See [Localization](localization.md).

# Routing

Craft includes a highly flexible and expressive routing engine mapped via the `Route` facade. The routes map incoming HTTP request methods and paths directly to controller actions or closure handlers.

Routes are defined inside the `routes/` directory:
- `routes/web.py` for standard browser-based HTML routes (supporting session state, cookie-based auth, CSRF validations, and template responses).
- `routes/api.py` for stateless JSON API routes (typically prefixed with `/api`).

The starter application's canonical login route is `GET /login` (named `login`),
with credentials submitted to `POST /login` (named `login.attempt`). A `GET
/signin` request redirects to `/login` for links that use that spelling. New
links should use the named `login` route; the redirect does not handle login
submissions.
See [Authentication](authentication.md) for the complete starter route contract
and middleware flow.

---

## Basic Routes

You map paths to a controller action using a list with the controller class and the string action name:

```python
from craft.facades import Route
from app.Http.Controllers.Blog.PostController import PostController

# Basic GET route
Route.get("/posts", [PostController, "index"]).name("posts.index")

# POST route
Route.post("/posts", [PostController, "store"]).name("posts.store")
```

Other supported HTTP verbs include:
```python
Route.put("/posts/{id}", [PostController, "update"])
Route.patch("/posts/{id}", [PostController, "patch"])
Route.delete("/posts/{id}", [PostController, "destroy"])
```

---

## Route Parameters

You capture dynamic path parameters using curly braces `{}`. These are parsed and passed as keyword arguments to the mapped controller action:

```python
# Route mapping
Route.get("/posts/{id}", [PostController, "show"]).name("posts.show")

# Controller Action
class PostController(Controller):
    def show(self, request, id: str):
        post = Post.find_or_fail(id)
        return self.view("posts.show", {"post": post})
```

---

## Route Named Access

You can chain `.name()` to name a route. This decouples your HTML templates and controller redirects from hardcoded URLs.
In Python code, generate URLs with `Route.url_for()`; inside Forge templates, the `route()` helper does the same:

```python
from craft.facades import Route

# Generate path
url = Route.url_for("posts.show", id="some-uuid-value")  # '/posts/some-uuid-value'
```

`url_for` URL-encodes parameter values, raises `ValueError` when a path
parameter is missing, and appends any extra parameters as a query string:

```python
Route.url_for("posts.index", page=2)   # '/posts?page=2'
```

There is no global Python `route()` function — that helper exists only inside
Forge templates.

---

## Route Groups

Grouping allows you to apply bulk attributes—such as route prefixes, shared middleware, or name prefixes—to multiple routes at once:

```python
Route.group(
    lambda: (
        Route.get("/dashboard", [AdminController, "index"]).name("dashboard"),
        Route.get("/settings", [AdminController, "settings"]).name("settings"),
    ),
    prefix="/admin",
    middleware=["auth"],
    name="admin.",
)
```
- Mapped URLs: `/admin/dashboard`, `/admin/settings`
- Route names: `admin.dashboard`, `admin.settings`
- Middleware applied: `auth` middleware group/class.

---

## Resource Controllers

A single call to `Route.resource` maps standard RESTful operations on a resource to their corresponding controller actions:

```python
Route.resource("posts", PostController)
```

The resource mapper registers the following routes:

| Verb | Path | Action | Route Name | Description |
|---|---|---|---|---|
| GET | `/posts` | `index` | `posts.index` | List posts |
| GET | `/posts/create` | `create` | `posts.create` | Form to create post |
| POST | `/posts` | `store` | `posts.store` | Store a new post |
| GET | `/posts/{id}` | `show` | `posts.show` | Display a post |
| GET | `/posts/{id}/edit`| `edit` | `posts.edit` | Form to edit post |
| PUT | `/posts/{id}` | `update` | `posts.update` | Update a post |
| DELETE | `/posts/{id}` | `destroy` | `posts.destroy`| Delete a post |

The resource mapper registers `PUT` only for updates — register a `Route.patch(...)` route yourself if you also want `PATCH`. Parameters use `{id}`, so the action signature is `def update(self, request, id)`.

Use `Route.api_resource` to exclude `create` and `edit` routes when mapping REST APIs.

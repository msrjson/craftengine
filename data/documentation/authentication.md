# Authentication in Craft Engine

Routes are explicit declarations. Inspect `routes/web.py` and run
`craft route:list` before using an authentication URL in an application.

| Concept | In Craft | Verify in |
| --- | --- | --- |
| Route declarations | `routes/web.py` | The project's own file |
| Checking credentials | `Auth.attempt(credentials)` | `engine/auth/manager.py` |
| Requiring sign-in | `.middleware("auth")` | `engine/http/kernel.py` and `middleware.py` |
| Linking to sign-in | `Route.url_for("login")` or `redirect(route="login")` | Registered route names |

Craft registers no login handler by convention; `craft make:auth` writes one.

## Starter application routes

A new project has none of these routes. `craft make:auth` writes them into
`routes/web.py`:

| Method | Path | Name | Purpose |
| --- | --- | --- | --- |
| GET | `/login` | `login` | Render the sign-in form. |
| POST | `/login` | `login.attempt` | Check the honeypot, the anti-spam trap and the credentials; throttled. |
| GET | `/signin` | - | Redirect an old or mistaken link to `/login`. |
| GET | `/register` | `register` | Render the registration form. |
| POST | `/register` | `register.store` | Register a user; throttled. |
| POST | `/logout` | `logout` | End the session. |
| GET | `/dashboard` | `dashboard` | A signed-in placeholder page; requires `auth`. |

A successful sign-in redirects to the named `home` route when the project has
one, and to `dashboard` otherwise. `craft make:admin` adds `/admin`, which
requires `auth` and `role:admin`.

`/signin` accepts navigation only. Submit credentials to `POST /login`; a
`POST /signin` request is not a login attempt. Generate links with the named
`login` route rather than writing either URL directly into new Python code.

## Request flow

1. `app/Providers/RouteServiceProvider.py` loads `routes/web.py` at boot.
2. `bootstrap/app.py` registers the global middleware in order. `StartSession`
   opens the session, `VerifyCsrfToken` checks state-changing browser requests,
   then `Authenticate` resolves the user stored in the session.
3. Route middleware is additional. `auth` runs `RequireAuth`, which redirects
   an unauthenticated browser request to `/login`. `role:admin` makes a separate
   authorization decision. The global `Authenticate` middleware identifies a
   user; it does not protect every route.
4. `AuthController.login` checks CAPTCHA and calls `Auth.attempt`. On success,
   `AuthManager` regenerates the session ID and stores the user ID. On the next
   request, the global `Authenticate` middleware restores the user.
5. `AuthController.logout` calls `Auth.logout`, which invalidates the session.

The global CSRF check applies to the browser's POST routes, including login and
logout. Keep the login form's `@csrf` directive. The login and registration POST
routes also declare `throttle`; the login action checks CAPTCHA. An `auth` alias
proves identity, while an authorizing alias or `Gate` protects privileged data.

## Before changing authentication

Read `routes/web.py`, `bootstrap/app.py`, `app/Http/Controllers/Auth/AuthController.py`,
`engine/auth/manager.py`, and `engine/http/middleware.py`. Then inspect the
effective route list and verify guest, signed-in user, and administrator behavior.
These files define the contract; verify there rather than from memory.

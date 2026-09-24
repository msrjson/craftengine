# Authentication in Craft Engine

Craft uses familiar Laravel-style facades, but the application's routes are
explicit declarations. Inspect `routes/web.py` and run `python dev.py route list`
before using an authentication URL in an application.

| Laravel concept | Craft equivalent | Verify in |
| --- | --- | --- |
| `routes/web.php` | `routes/web.py` | Application route declarations |
| `Auth::attempt($credentials)` | `Auth.attempt(credentials)` | `engine/auth/manager.py` |
| `auth` route middleware | `.middleware("auth")` | `engine/http/kernel.py` and `middleware.py` |
| `route('login')` | `Route.url_for("login")` or `redirect(route="login")` | Registered route names |

This table maps concepts, not Laravel packages or automatically generated URLs.
Craft does not register a `/signin` login handler through a convention.

## Starter application routes

| Method | Path | Name | Purpose |
| --- | --- | --- | --- |
| GET | `/login` | `login` | Render the login form. |
| POST | `/login` | `login.attempt` | Check CAPTCHA and credentials; throttled. |
| GET | `/signin` | — | Redirect an old or mistaken link to `/login`. |
| GET | `/register` | `register` | Render the registration form. |
| POST | `/register` | `register.store` | Register a user; throttled. |
| POST | `/logout` | `logout` | End the session. |
| GET | `/panel` | `panel.index` | Signed-in user's workspace; requires `auth`. |
| GET | `/admin` | `admin.dashboard` | Administration; requires `auth` and `role:admin`. |

The starter redirects a successful login to the named `home` route. The
`/dashboard` URL is also registered by the starter and is not the protected
control panel. Use `/panel` for the signed-in user's workspace.

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
The Laravel analogy is a learning aid; these Craft files define the contract.

# Deploying behind a reverse proxy

Craft Engine is an **ASGI application**: it serves HTTP from a long-running
Python process, and Apache, nginx or another HTTP server stands in front of it
as a reverse proxy. If you come from PHP-style hosting, that is the one
structural difference — a PHP host runs a script per request, Craft Engine is a
process that stays up. Everything else follows from it.

Nothing in the framework is executed per request by the web server: there is no
`mod_wsgi`, `mod_php` or CGI entry point, and pointing the web server at
`public/` and expecting it to run the application does not work. The server
proxies to the process instead.

That is not a limitation to work around. The concurrency model (a thread pool
borrowing pooled database connections), the ASGI lifespan that drains in-flight
requests on `SIGTERM`, and the connection budget all assume a process that
lives between requests — see [Deployment](deployment.md#concurrency).

## What the host must offer

| Requirement | Why |
|---|---|
| A process that stays up | `gunicorn`/`uvicorn` serves the application; the web server only forwards to it |
| A supervisor or container runtime | systemd, supervisord or a container restarts it; the framework does not daemonise itself |
| An internal address | the application binds `127.0.0.1:9000` (or a private container port); only the proxy is public |

What this rules out: shared hosting that only executes a script per request. The
application needs somewhere to keep a process alive — a server you control, a
VPS, or a container platform.

## Start the application

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker public.index:application \
  --bind 127.0.0.1:9000
```

`uvicorn public.index:application --host 127.0.0.1 --port 9000 --workers 4` is
equivalent. Bind to an internal address so only the proxy reaches it; the full
production checklist is in [Deployment](deployment.md).

## Apache

Enable the proxy modules once:

```bash
a2enmod proxy proxy_http headers
```

```apache
<VirtualHost *:443>
    ServerName app.example.com
    # ... TLS configuration ...

    # Keep the browser's Host: the redirect and the CSRF origin check trust it.
    ProxyPreserveHost On

    ProxyPass        / http://127.0.0.1:9000/
    ProxyPassReverse / http://127.0.0.1:9000/

    # Tell the application the original scheme, so https URLs are built.
    RequestHeader set X-Forwarded-Proto "https"

    # The engine defines no WebSocket routes. Add an upgrade block
    # (mod_proxy_wstunnel) only if the application adds some.
</VirtualHost>
```

## nginx

```nginx
server {
    listen 443 ssl;
    server_name app.example.com;
    # ... TLS configuration ...

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

## Telling the application about the proxies

Two things must be right, or the application sees the wrong client and builds
the wrong URLs.

**The client address.** `X-Forwarded-For` is written by the client and only
appended to by each proxy, so its left-most entry is whatever the client chose.
The framework reads it **from the right**, skipping exactly as many hops as the
deployment declares:

```dotenv
TRUSTED_PROXY_HOPS=1     # one Apache or nginx in front of the application
```

`0` (the default) ignores the header and uses the connection address. Set it to
the number of proxies *you* run — too low lets a client choose its own address,
too high trusts a proxy's own address. The reading lives in
`engine/security/net.py` and feeds `Request.ip()` and the firewall.

**The public address.** `APP_URL` must be the address the browser uses, and the
proxy must preserve the incoming `Host`: `redirect.back()` and the CSRF origin
check accept the request's own host *or* the `APP_URL` host
(`engine/http/response.py`). Behind a proxy that rewrites the host, an error
redirect would otherwise land on the internal name.

```dotenv
APP_URL=https://app.example.com
SESSION_SECURE_COOKIE=true
```

## Health checks and metrics behind the proxy

Both probes ship off until a flag turns them on, and are dispatched outside the
middleware stack, so a proxy or load balancer can poll them without a session:

```dotenv
HEALTH_ROUTES_ENABLED=true
```

Point the load balancer at `/ready` without a token and the alerting scraper at
`/ready` with `HEALTH_READINESS_TOKEN`; `/metrics` needs its own token. See
[Health checks](deployment.md#health-checks).

## Checklist

- [ ] `gunicorn` (or `uvicorn`) runs under systemd, supervisord or a container.
- [ ] The application binds an internal address; only the proxy is public.
- [ ] The proxy preserves `Host` (`ProxyPreserveHost On` / `proxy_set_header Host $host`).
- [ ] `X-Forwarded-Proto` is set for HTTPS.
- [ ] `TRUSTED_PROXY_HOPS` equals the number of proxies you run.
- [ ] `APP_URL` is the public address and `SESSION_SECURE_COOKIE=true`.
- [ ] `/health` or `/ready` is enabled and wired to the load balancer.

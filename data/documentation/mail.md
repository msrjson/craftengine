# Mail & Notification Subsystem

Craft Engine provides a fluent, driver-agnostic email and notification delivery system.

## 🚀 Sending Emails

### 1. Fluent One-Liner / Raw Email
```python
from craft.facades import Mail

# Send simple plain text email
Mail.raw("Your verification code is 481920", to="user@example.com", subject="Verify Account")

# Fluent chain
Mail.to("user@example.com").cc("manager@example.com").raw("Meeting rescheduled to 3 PM", subject="Meeting Update")
```

---

### 2. Template-Driven Mailable Class
Create a declarative `Mailable` subclass:

```python
# app/Mail/WelcomeUserMailable.py
from craft.mail.mailable import Mailable

class WelcomeUserMailable(Mailable):
    subject = "Welcome to our Platform!"

    def __init__(self, user):
        super().__init__()
        self.user = user

    def build(self):
        return self.view("emails.welcome", {"user": self.user})
```

Dispatch it easily:
```python
from craft.facades import Mail
from app.Mail.WelcomeUserMailable import WelcomeUserMailable

Mail.to(user.email).send(WelcomeUserMailable(user))
```

---

## 🛠️ Transports (`smtp`, `log`, `array`)
Configured in `config/mail.py`:
- `smtp`: Standard production SMTP delivery with TLS/SSL authentication.
- `log`: Writes outgoing emails to the application logger (`storage/logs/craft.log`).
- `array`: In-memory driver for rapid, deterministic testing (`Mail.set_default_mailer('array')`).

## Failover and quotas

A mailer can name a `fallback`, and one that fails or is over its quota hands
the message to the next in the chain, so a single provider outage or cap does
not lose the notification. A mailer may also carry a `quota`:

```python
# config/mail.py
"mailers": {
    "smtp": {
        "transport": "smtp",
        "fallback": ["smtp_backup", "log"],       # tried in order
        "quota": {"limit": 5000, "window": 3600, "per_tenant": True},
    },
    "smtp_backup": {"transport": "smtp", "host": "backup.example.com"},
    "log": {"transport": "log"},
}
```

At most `limit` messages are sent per `window` seconds; `0` disables the quota.
With `per_tenant` the count is kept for the bound tenant alone, so one tenant
cannot spend another's. `Mail.to(...).send(...)` returns `True` only when a
mailer accepted the message; when every mailer is over quota it returns `False`
and logs why.


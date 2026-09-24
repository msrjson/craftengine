"""Session configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

#: "cookie" keeps the payload in a signed cookie; "file" keeps it under
#: storage/framework/sessions and puts only a signed id in the cookie;
#: "database" keeps it in the `sessions` table and puts only a signed id in
#: the cookie -- the only driver a session can be revoked from outside the
#: browser that holds it (an admin ending a compromised session, "log out
#: everywhere," a password change invalidating every other session).
driver = env("SESSION_DRIVER", "cookie")

#: Seconds a session stays valid, from creation, regardless of activity.
lifetime = env("SESSION_LIFETIME", 7200)

#: Seconds of inactivity before a session times out, independent of
#: `lifetime` -- "database" driver only. Empty disables idle checking.
idle_timeout = env("SESSION_IDLE_TIMEOUT", "")

cookie = env("SESSION_COOKIE", "craft_session")

#: Send the cookie only over HTTPS. Turn this on in production.
secure = env("SESSION_SECURE_COOKIE", False)

#: "lax" blocks the cookie on cross-site POSTs while keeping normal links working.
same_site = env("SESSION_SAME_SITE", "lax")

#: Master switch for CSRF verification. Only turn this off for a stateless API.
csrf = env("SESSION_CSRF", True)

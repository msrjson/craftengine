"""Application configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
from craft.config import env

APP_NAME = env("APP_NAME", "Craft")
APP_ENV = env("APP_ENV", "local")
# Debug must be opted into (.env sets it) - defaulting on leaks stack traces
# in production.
APP_DEBUG = env("APP_DEBUG", False)
APP_URL = env("APP_URL", "http://localhost:8000")
APP_KEY = env("APP_KEY", "")
#: Reverse proxies between the internet and this process. `X-Forwarded-For` is
#: read from the right, skipping this many hops; `0` ignores the header. Measure
#: the topology before changing it -- too high trusts a proxy's own address, too
#: low lets the client choose its address.
trusted_proxy_hops = env("TRUSTED_PROXY_HOPS", 0)
APP_LOCALE = env("APP_LOCALE", "en")
APP_FALLBACK_LOCALE = env("APP_FALLBACK_LOCALE", "en")
#: The single clock `ScheduleManager` (`engine/schedule/manager.py`) reads
#: `now` from -- an IANA zone name (e.g. `"America/Sao_Paulo"`), not an offset.
#: Everything the framework WRITES stays UTC (`engine/orm/model.py`,
#: `soft_deletes.py`, `queue/`) regardless of this setting; this only decides
#: what wall-clock hour a cron expression like `daily_at("02:00")` means, so a
#: schedule fires at 2am local time on this server's clock, not 2am UTC on a
#: server in a different timezone. Previously absent on purpose because
#: nothing read it - the scheduler is what reintroduces it.
APP_TIMEZONE = env("APP_TIMEZONE", "UTC")
# The framework's own version, from the package - it used to be hardcoded to
# "v3.11", which is the minimum Python version, not a release of Craft.
from craft import __release__ as APP_RELEASE  # noqa: E402
from craft import __version__ as APP_VERSION  # noqa: E402

#: Locales offered by the language switcher, most specific first.
APP_LOCALES = ["en", "pt", "pt-BR", "es"]

version = APP_VERSION

#: `config('app.release')` is read by the layout footer and the version badge.
#: It had no declaration at all, so both rendered blank; and `config/framework.py`
#: carried a second, hand-maintained copy that had already drifted out of step
#: with the package. The package is the single source of truth.
release = APP_RELEASE

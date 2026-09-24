"""MSR JSON manifest (https://msrjson.org), served at /.well-known/msr.json.

Every Craft application describes itself to software registries and AI agents
through this manifest. Fill in what only the owner knows; everything left empty
is omitted from the manifest rather than guessed. The descriptions are the
translation keys `msr.entity.tagline`, `msr.entity.summary` and
`msr.entity.text`, one set per locale in `LOCALES`.

Guide: documentation/msr.md. Check the result with `python dev.py msr:validate`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env


def _list(key: str, default: str = "") -> list:
    """Split a comma-separated environment value into a list."""
    return [item.strip() for item in str(env(key, default) or "").split(",") if item.strip()]


# Set MSR_ENABLED=true to publish the manifest at /.well-known/msr.json.
#
# Off by default: the manifest states the exact version, release date, vendor
# and pricing of this installation, which is the most useful single input for
# matching a published vulnerability to a running instance. Publishing it is a
# decision the owner makes about this product, not a route an application
# acquires by existing.
ENABLED = env("MSR_ENABLED", False)

#: The product name and the public URL. The domain is taken from the URL unless
#: MSR_DOMAIN names it; a host without a dot (localhost) disables the manifest.
NAME = env("MSR_NAME", env("APP_NAME", "Craft"))
URL = env("MSR_URL", env("APP_URL", ""))
DOMAIN = env("MSR_DOMAIN", "")
#: Empty derives it from NAME: "Craft Engine" -> "craft-engine".
SLUG = env("MSR_SLUG", "")
#: saas | ai-agent | mcp-server | api | software | open-source | framework |
#: library | plugin | extension | desktop | mobile
TYPE = env("MSR_TYPE", "saas")

#: Omitted unless MSR_LICENSE_TYPE is set. commercial_terms and pricing model
#: are different enums: "usage" is a pricing model only.
LICENSE = {
    "type": env("MSR_LICENSE_TYPE"),
    "spdx_id": env("MSR_LICENSE_SPDX"),
    "commercial_terms": env("MSR_LICENSE_TERMS"),
} if env("MSR_LICENSE_TYPE") else {}

#: The product's owner. Omitted unless MSR_VENDOR_NAME is set; the website
#: defaults to URL. country_code is ISO 3166-1 alpha-2, upper case.
VENDOR = {
    "name": env("MSR_VENDOR_NAME"),
    "website": env("MSR_VENDOR_WEBSITE"),
    "country_code": env("MSR_VENDOR_COUNTRY"),
    "support_url": env("MSR_SUPPORT_URL"),
} if env("MSR_VENDOR_NAME") else {}

#: cloud | self-hosted | on-premise | hybrid | desktop | mobile | edge | docker
DEPLOYMENT = _list("MSR_DEPLOYMENT", "cloud")
INTEGRATIONS = _list("MSR_INTEGRATIONS")

#: free | freemium | subscription | usage | one-time | quote. Omitted when unset.
PRICING = {
    "model": env("MSR_PRICING_MODEL"),
    "starting_price_cents": env("MSR_STARTING_PRICE_CENTS"),
    "currency": env("MSR_CURRENCY"),
} if env("MSR_PRICING_MODEL") else {}

#: Empty reads [project].version from pyproject.toml and its dated heading in
#: CHANGELOG.md. PUBLISHED_AT is RFC 3339 with a timezone: 2026-09-16T00:00:00Z.
VERSION = env("MSR_VERSION", "")
PUBLISHED_AT = env("MSR_PUBLISHED_AT", "")
#: major | minor | patch | security | initial
RELEASE_TYPE = env("MSR_RELEASE_TYPE", "")
CHANGELOG_URL = env("MSR_CHANGELOG_URL", "")

#: Locales whose descriptions are published, keyed by these codes.
LOCALES = ["en", "pt-BR", "es"]

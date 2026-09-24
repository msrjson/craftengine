"""Security response headers configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

csp = {
    #: The policy applied when no more specific prefix below matches.
    "default": env("CSP_DEFAULT_POLICY", ""),
    #: Path-prefix overrides -- the longest matching prefix wins, so
    #: `/admin/reports` matches `/admin` over a bare `/`. An admin area and a
    #: public marketing site legitimately need different policies (the admin
    #: console may need no inline scripts at all; a CMS-rendered page might).
    "prefixes": {
        # "/admin": "default-src 'self'; script-src 'self'",
    },
    #: Send `Content-Security-Policy-Report-Only` instead of the enforcing
    #: header -- violations are reported (if `report_uri` is set) but nothing
    #: is blocked. For rolling out a new or changed policy and watching what
    #: it *would* have broken before it can break real traffic.
    "report_only": env("CSP_REPORT_ONLY", False),
    #: Where the browser POSTs a violation report. Empty disables reporting
    #: even in report-only mode -- the policy still applies (or would, if
    #: enforcing), it just goes unwatched.
    "report_uri": env("CSP_REPORT_URI", ""),
}

hsts = env("HSTS_POLICY", "")

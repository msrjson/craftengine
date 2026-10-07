"""Cookieless SEO: server-side slugs and metadata.

Everything here is computed on the server from the page's own title, body and
URL. Nothing reads or writes a cookie and nothing tracks a visitor, so the
metadata stands on its own under a consent-free or cookie-less policy.
"""

from __future__ import annotations

from plugins.seo.engine import Seo, SeoAudit

__all__ = ["Seo", "SeoAudit"]

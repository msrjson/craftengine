"""Cookieless SEO — plugin descriptor and registration."""

from plugins.seo.engine import Seo

PLUGIN = {
    "slug": "seo",
    "name": "Cookieless SEO",
    "version": "1.0.0",
    "description": (
        "Server-side slugification, canonical URLs, meta tags and a content "
        "audit; no cookie is read or written."
    ),
}


def register(app) -> None:
    """Bind the SEO service into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("seo", lambda _container: Seo())


__all__ = ["PLUGIN", "register", "Seo"]

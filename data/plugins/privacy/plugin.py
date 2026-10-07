"""Privacy kit — plugin descriptor and registration."""

from plugins.privacy.engine import LegalPage, Privacy

PLUGIN = {
    "slug": "privacy",
    "name": "Privacy Kit",
    "version": "1.0.0",
    "description": (
        "Subject data portability (a deterministic export bundle) and the legal-page "
        "contract (privacy, terms, cookies) as keys, never copy."
    ),
}


def register(app) -> None:
    """Bind the privacy service into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("privacy", lambda _container: Privacy())


__all__ = ["PLUGIN", "register", "Privacy", "LegalPage"]

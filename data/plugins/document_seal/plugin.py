"""Document seal — plugin descriptor and registration."""

from plugins.document_seal.seal import DocumentSeal, Seal

PLUGIN = {
    "slug": "document_seal",
    "name": "Document Seal",
    "version": "1.0.0",
    "description": "Tamper-evident document seals: SHA-256, or HMAC when a key is given.",
}


def register(app) -> None:
    """Bind the seal service into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("document_seal", lambda _container: DocumentSeal())


__all__ = ["PLUGIN", "register", "DocumentSeal", "Seal"]

"""PIX — plugin descriptor and registration."""

from plugins.pix.engine import Pix, PixCharge

PLUGIN = {
    "slug": "pix",
    "name": "PIX BR Code",
    "version": "1.0.0",
    "description": "Build and verify PIX BR Code (EMV) payloads for static and dynamic charges.",
}


def register(app) -> None:
    """Bind the PIX service into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("pix", lambda _container: Pix())


__all__ = ["PLUGIN", "register", "Pix", "PixCharge"]

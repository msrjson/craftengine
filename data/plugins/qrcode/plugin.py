"""QR code — plugin descriptor and registration."""

from plugins.qrcode.engine import QrCode

PLUGIN = {
    "slug": "qrcode",
    "name": "QR Code",
    "version": "1.0.0",
    "description": "Generate real, scannable QR codes (SVG, PNG, data URI) with segno.",
}


def register(app) -> None:
    """Bind the QR service into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("qrcode", lambda _container: QrCode())


__all__ = ["PLUGIN", "register", "QrCode"]

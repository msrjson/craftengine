"""QR Code Generator Plugin — Native Capability Plugin Descriptor."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .engine import QRCodeGeneratorEngine

PLUGIN = {
    "slug": "qrcode_generator",
    "name": "QR Code Generator Plugin",
    "version": "1.0.0",
    "description": "Stateless SVG matrix vector QR code generation plugin.",
}


def register(app):
    """Bind the QRCodeGeneratorEngine into the application IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("plugin.qrcode_generator", lambda c: QRCodeGeneratorEngine())

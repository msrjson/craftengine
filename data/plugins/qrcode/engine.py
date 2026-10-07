"""QrCode — generate real, scannable QR codes.

The encoder is `segno`, a maintained pure-Python library: a hand-rolled matrix
would look like a QR code and not scan. The service returns the rendered image
(SVG text or PNG bytes) and a data URI for embedding.
"""

from __future__ import annotations

import base64
import io

import segno

DEFAULT_SCALE = 10
DEFAULT_BORDER = 4
DEFAULT_DARK = "#000000"
DEFAULT_LIGHT = "#ffffff"


class QrCode:
    """Stateless QR code generation. Pure functions of their arguments."""

    @staticmethod
    def _make(content: str, error: str) -> "segno.QRCode":
        text = str(content or "")
        if not text:
            raise ValueError("qrcode_content_empty")
        return segno.make(text, error=error)

    @staticmethod
    def svg(
        content: str,
        scale: int = DEFAULT_SCALE,
        border: int = DEFAULT_BORDER,
        dark: str = DEFAULT_DARK,
        light: str = DEFAULT_LIGHT,
        error: str = "m",
    ) -> str:
        """Return the QR code as SVG markup."""
        buffer = io.BytesIO()
        QrCode._make(content, error).save(
            buffer, kind="svg", scale=scale, border=border, dark=dark, light=light
        )
        return buffer.getvalue().decode("utf-8")

    @staticmethod
    def png(
        content: str,
        scale: int = DEFAULT_SCALE,
        border: int = DEFAULT_BORDER,
        dark: str = DEFAULT_DARK,
        light: str = DEFAULT_LIGHT,
        error: str = "m",
    ) -> bytes:
        """Return the QR code as PNG bytes."""
        buffer = io.BytesIO()
        QrCode._make(content, error).save(
            buffer, kind="png", scale=scale, border=border, dark=dark, light=light
        )
        return buffer.getvalue()

    @staticmethod
    def data_uri(content: str, **options: object) -> str:
        """Return the QR code as a `data:` URI, ready to place in an `img src`."""
        encoded = base64.b64encode(QrCode.png(content, **options)).decode("ascii")
        return f"data:image/png;base64,{encoded}"


__all__ = ["QrCode", "DEFAULT_SCALE", "DEFAULT_BORDER", "DEFAULT_DARK", "DEFAULT_LIGHT"]

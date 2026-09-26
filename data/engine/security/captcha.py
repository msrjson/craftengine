"""
Captcha — Short alphanumeric challenge held in the session, single-use (the
stored code is cleared on every validation attempt, pass or fail), shown to
the visitor only as a raster image.
Category: Core Framework (Security).
Relations:
  - Bound as `captcha`, exposed via the `Captcha` facade. Uses
    `secrets.compare_digest` for the comparison.
  - Rendered with Pillow (a declared dependency, also used by `engine/media`).
References:
  - Guide: `documentation/security.md#captcha-integration`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import io
import secrets
from typing import Any

def _pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont

        return Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required to generate captcha images. Run `pip install pillow`.") from exc


class Captcha:
    """Generates and validates a short alphanumeric challenge held in session.

    The code never appears as text in the page. It used to be rendered as one
    rotated `<span>` per character, which a script reads straight from the DOM.
    """

    LENGTH = 5
    #: No O/0 or I/1: a human cannot tell them apart in a distorted image.
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    WIDTH = 150
    HEIGHT = 44
    SESSION_KEY = "captcha_code"

    @staticmethod
    def generate(request: Any) -> str:
        """Create a new code and store it in the session.

        Args:
            request: The current request; its session holds the code.

        Returns:
            The generated code, for rendering with `image_data_uri`.
        """
        code = "".join(secrets.choice(Captcha.ALPHABET) for _ in range(Captcha.LENGTH))
        if hasattr(request, "session"):
            request.session().put(Captcha.SESSION_KEY, code)
        return code

    @staticmethod
    def _glyph(character: str, font: Any) -> Any:
        Image, ImageDraw, _ = _pillow()
        tile = Image.new("RGBA", (30, 40), (0, 0, 0, 0))
        shade = tuple(secrets.randbelow(90) for _ in range(3)) + (255,)
        ImageDraw.Draw(tile).text((6, 4), character, font=font, fill=shade)
        return tile.rotate(secrets.randbelow(51) - 25, resample=Image.BICUBIC, expand=False)

    @staticmethod
    def _add_noise(canvas: Any) -> None:
        _, ImageDraw, _ = _pillow()
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        for _ in range(6):
            points = [(secrets.randbelow(width), secrets.randbelow(height)) for _ in range(2)]
            draw.line(points, fill=(120 + secrets.randbelow(100),) * 3, width=1)
        for _ in range(140):
            draw.point((secrets.randbelow(width), secrets.randbelow(height)), fill=(150,) * 3)

    @staticmethod
    def render_png(code: str) -> bytes:
        """Draw `code` as a distorted PNG image.

        Args:
            code: The challenge to draw.

        Returns:
            The PNG bytes.
        """
        Image, _, ImageFont = _pillow()
        font = ImageFont.load_default(size=28)
        canvas = Image.new("RGB", (Captcha.WIDTH, Captcha.HEIGHT), (241, 245, 249))
        for index, character in enumerate(code):
            glyph = Captcha._glyph(character, font)
            canvas.paste(glyph, (4 + index * 28, secrets.randbelow(5)), glyph)
        Captcha._add_noise(canvas)
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def image_data_uri(code: str) -> str:
        """Return the challenge image as a `data:` URI for an `<img src>`.

        Args:
            code: The challenge to draw.

        Returns:
            A `data:image/png;base64,...` URI.
        """
        return "data:image/png;base64," + base64.b64encode(Captcha.render_png(code)).decode("ascii")

    @staticmethod
    def get_obfuscated_html(code: str) -> str:
        """Deprecated: pass `image_data_uri(code)` to the template instead.

        Kept for backward compatibility (NR-05). It now returns an image, so the
        code no longer appears in the markup.

        Args:
            code: The challenge to draw.

        Returns:
            An `<img>` element carrying the challenge image.
        """
        return (
            f'<img class="craft-captcha" src="{Captcha.image_data_uri(code)}" '
            f'width="{Captcha.WIDTH}" height="{Captcha.HEIGHT}" alt="">'
        )

    @staticmethod
    def validate(request: Any, code: str) -> bool:
        """Compare against the stored code, clearing it to prevent replay.

        Args:
            request: The current request.
            code: The code the visitor typed.

        Returns:
            Whether the code matches the one in the session.
        """
        if not hasattr(request, "session"):
            return False

        stored = request.session().get(Captcha.SESSION_KEY)
        # Always clear, whether or not the attempt succeeds — a captcha is
        # single-use, otherwise it can be brute-forced against one challenge.
        request.session().forget(Captcha.SESSION_KEY)

        if not stored or not code:
            return False
        return secrets.compare_digest(str(stored).upper(), str(code).strip().upper())

"""Tests for the QR code plugin (`plugins/qrcode/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest

from engine.plugins.manager import PluginManager
from plugins.qrcode import QrCode

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class TestQrCode:
    def test_svg_output_is_markup(self):
        svg = QrCode.svg("https://craftengine.org")
        assert "<svg" in svg and svg.strip().endswith("</svg>")

    def test_png_output_is_a_png(self):
        png = QrCode.png("https://craftengine.org")
        assert png.startswith(PNG_MAGIC)

    def test_different_content_gives_different_output(self):
        assert QrCode.png("one") != QrCode.png("two")

    def test_a_data_uri_carries_a_png(self):
        uri = QrCode.data_uri("hello")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > len("data:image/png;base64,")

    def test_empty_content_is_refused(self):
        with pytest.raises(ValueError) as raised:
            QrCode.svg("")
        assert str(raised.value) == "qrcode_content_empty"


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "qrcode" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.qrcode.plugin import register

        register(app)
        assert isinstance(app.make("qrcode"), QrCode)

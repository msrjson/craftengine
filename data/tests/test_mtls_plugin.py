"""Tests for the mutual TLS channel plugin (`plugins/mtls/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import datetime
import os
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from engine.plugins.manager import PluginManager
from plugins.mtls.channel import ChannelError, forget_contexts, ssl_context


def _certificate_pair() -> tuple[str, str]:
    """Return a fresh, self-signed certificate and key, both PEM encoded."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "craft-mtls-test")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    return cert_pem, key_pem


class TestChannel:
    def setup_method(self):
        forget_contexts()

    def test_a_valid_pair_yields_an_ssl_context(self):
        cert_pem, key_pem = _certificate_pair()
        context = ssl_context(cert_pem, key_pem)
        assert isinstance(context, ssl.SSLContext)

    def test_the_same_material_is_cached(self):
        cert_pem, key_pem = _certificate_pair()
        assert ssl_context(cert_pem, key_pem) is ssl_context(cert_pem, key_pem)

    def test_forget_rebuilds_the_context(self):
        cert_pem, key_pem = _certificate_pair()
        first = ssl_context(cert_pem, key_pem)
        forget_contexts()
        assert ssl_context(cert_pem, key_pem) is not first

    def test_missing_material_is_refused(self):
        with pytest.raises(ChannelError) as raised:
            ssl_context("", "key")
        assert raised.value.code == "CHANNEL_MATERIAL_MISSING"
        assert raised.value.message_key == "mtls.errors.material_missing"

    def test_a_bad_pair_is_refused(self):
        cert_pem, _ = _certificate_pair()
        _, other_key = _certificate_pair()
        with pytest.raises(ChannelError) as raised:
            ssl_context(cert_pem, other_key)
        assert raised.value.code == "CHANNEL_PAIR_REJECTED"


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "mtls" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.mtls.plugin import MutualTlsChannel, register

        register(app)
        assert isinstance(app.make("mtls"), MutualTlsChannel)

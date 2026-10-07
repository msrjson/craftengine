"""Tests for the PIX BR Code plugin (`plugins/pix/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from engine.plugins.manager import PluginManager
from plugins.pix import Pix
from plugins.pix.emv import crc16


class TestCrc16:
    def test_the_standard_check_value(self):
        # CRC16/CCITT-FALSE of "123456789" is 0x29B1 by definition.
        assert crc16("123456789") == "29B1"


class TestBrcode:
    def test_the_payload_carries_the_required_fields(self):
        charge = Pix.brcode("user@example.com", "Loja do Zé", "São Paulo", amount=10.5)
        fields = Pix.fields(charge.payload)

        assert fields["00"] == "01"
        assert fields["01"] == "11"  # static
        assert fields["26"].startswith("0014BR.GOV.BCB.PIX")
        assert "user@example.com" in fields["26"]
        assert fields["53"] == "986"
        assert fields["54"] == "10.50"
        assert fields["58"] == "BR"
        assert fields["59"] == "LOJA DO ZE"
        assert fields["60"] == "SAO PAULO"

    def test_the_payload_verifies(self):
        charge = Pix.brcode("user@example.com", "Store", "City")
        assert Pix.verify(charge.payload) is True

    def test_a_changed_payload_does_not_verify(self):
        charge = Pix.brcode("user@example.com", "Store", "City")
        tampered = charge.payload[:-1] + ("0" if charge.payload[-1] != "0" else "1")
        assert Pix.verify(tampered) is False

    def test_a_dynamic_charge_marks_itself_single_use(self):
        charge = Pix.brcode("user@example.com", "Store", "City", dynamic=True)
        assert charge.dynamic is True
        assert Pix.fields(charge.payload)["01"] == "12"

    def test_the_amount_is_optional(self):
        charge = Pix.brcode("user@example.com", "Store", "City")
        assert charge.amount is None
        assert "54" not in Pix.fields(charge.payload)

    def test_the_default_txid_is_the_star_marker(self):
        charge = Pix.brcode("user@example.com", "Store", "City")
        assert charge.txid == "***"

    def test_a_custom_txid_is_kept_and_sanitized(self):
        charge = Pix.brcode("user@example.com", "Store", "City", txid="pedido-42")
        assert charge.txid == "PEDIDO-42"

    def test_an_empty_key_is_refused(self):
        try:
            Pix.brcode("", "Store", "City")
        except ValueError as error:
            assert str(error) == "pix_key_empty"
        else:
            raise AssertionError("an empty key must be refused")


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "pix" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.pix.plugin import register

        register(app)
        assert isinstance(app.make("pix"), Pix)

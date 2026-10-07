"""Tests for the document seal plugin (`plugins/document_seal/`)."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from engine.plugins.manager import PluginManager
from plugins.document_seal import DocumentSeal, Seal


class TestSeal:
    def test_sealing_the_same_content_twice_gives_the_same_digest(self):
        first = DocumentSeal.seal("contract text")
        second = DocumentSeal.seal("contract text")
        assert first.digest == second.digest
        assert first.keyed is False and first.algorithm == "sha256"

    def test_a_verified_seal_matches_the_content(self):
        seal = DocumentSeal.seal("contract text")
        assert DocumentSeal.verify("contract text", seal) is True

    def test_a_changed_document_does_not_verify(self):
        seal = DocumentSeal.seal("contract text")
        assert DocumentSeal.verify("contract text ", seal) is False

    def test_bytes_and_str_of_the_same_content_agree(self):
        assert DocumentSeal.seal("abc").digest == DocumentSeal.seal(b"abc").digest

    def test_a_keyed_seal_needs_the_key_to_verify(self):
        seal = DocumentSeal.seal("contract text", key="s3cret")
        assert seal.keyed is True
        assert DocumentSeal.verify("contract text", seal, key="s3cret") is True
        assert DocumentSeal.verify("contract text", seal, key="wrong") is False
        assert DocumentSeal.verify("contract text", seal) is False

    def test_an_unknown_algorithm_is_refused(self):
        seal = Seal(algorithm="md5", digest="x", sealed_at="now")
        assert DocumentSeal.verify("contract text", seal) is False


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "document_seal" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.document_seal.plugin import register

        register(app)
        assert isinstance(app.make("document_seal"), DocumentSeal)

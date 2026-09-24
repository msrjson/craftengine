"""Tests for Image and Media Facades in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import Image, Media
from tests.support.models import Media as MediaModel
from craft.facades import DB


class TestMediaFacades:
    def test_image_facade_new(self):
        img = Image.new(100, 100, color=(255, 0, 0, 255))
        assert img.dimensions == (100, 100)

    def test_media_facade_new_image(self):
        img = Media.new_image(80, 80)
        assert img.dimensions == (80, 80)

    def test_media_model_conversions_json(self, migrated_database):
        media = MediaModel.create({
            "model_type": "Post",
            "model_id": 1,
            "filename": "cover.jpg",
            "mime_type": "image/jpeg",
            "size": 1024,
            "width": 1920,
            "height": 1080,
            "conversions": '{"thumb": "cover_thumb.webp"}',
        })
        assert media.id is not None
        assert media.get_conversions()["thumb"] == "cover_thumb.webp"

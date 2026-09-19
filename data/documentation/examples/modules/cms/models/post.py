"""CMS Domain Post Model."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm import Model

from engine.orm.publishable import PublishableMixin
from engine.orm.sluggable import SluggableMixin


class Post(Model, SluggableMixin, PublishableMixin):
    """Domain model for CMS blog and article posts."""

    __table__ = "cms_posts"
    fillable = ["title", "slug", "body", "user_id", "status", "published_at"]
    slug_source_column = "title"

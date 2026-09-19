"""CMS Data Persistence Repository."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, List, Optional

from ..models.post import Post


class CmsRepository:
    """Isolated repository for CMS domain queries and operations."""

    def get_latest_posts(self, limit: int = 15) -> List[Post]:
        """Fetch latest published blog posts."""
        return Post.query().order_by_desc("created_at").take(limit).get()

    def find_post_by_id_or_uuid(self, identifier: str) -> Optional[Post]:
        """Find a post using public UUID or integer key."""
        return Post.find_by_route_key(identifier)

    def create_post(self, attributes: dict) -> Post:
        """Persist a new post record."""
        return Post.create(attributes)

    def get_all_media(self) -> List[Any]:
        """Fetch media library items."""
        return []

"""CMS Business Domain Service."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, List, Optional

from documentation.examples.plugins.seo_optimizer.engine import SeoOptimizerEngine

from ..models.post import Post
from ..repositories.cms_repository import CmsRepository
from ..schemas.cms_schema import CreatePostData


class CmsService:
    """Core domain business service managing CMS workflows."""

    def __init__(self, repository: Optional[CmsRepository] = None):
        self.repository = repository or CmsRepository()

    def list_posts(self) -> List[Post]:
        """Retrieve recent blog posts."""
        return self.repository.get_latest_posts()

    def get_post(self, identifier: str) -> Optional[Post]:
        """Find a blog post by public UUID or route key."""
        return self.repository.find_post_by_id_or_uuid(identifier)

    def create_post(self, data: CreatePostData) -> Dict[str, Any]:
        """Create a post, automatically running SEO optimization and slug generation."""
        slug = data.slug or SeoOptimizerEngine.slugify(data.title)
        seo_report = SeoOptimizerEngine.analyze_content(data.title, data.body)

        post = self.repository.create_post(
            {
                "title": data.title,
                "body": data.body,
                "user_id": data.user_id,
                "slug": slug,
            }
        )

        return {
            "post": post,
            "seo_analysis": {
                "readability_score": seo_report.readability_score,
                "suggestions": seo_report.suggestions,
            },
        }

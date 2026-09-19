"""CMS request DTOs and validation schemas."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass
from typing import Optional


@dataclass
class CreatePostData:
    """Data transfer object for blog post creation."""

    title: str
    body: str
    user_id: int
    slug: Optional[str] = None


@dataclass
class CreatePageData:
    """Data transfer object for static page creation."""

    title: str
    content: str
    slug: Optional[str] = None
    is_published: bool = True

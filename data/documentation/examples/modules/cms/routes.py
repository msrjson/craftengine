"""Route definitions for CMS Business Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .controllers.media_controller import MediaController
from .controllers.page_controller import PageController
from .controllers.post_controller import PostController


def register_routes(router):
    """Register HTTP routes for the CMS domain package."""
    router.get("/cms/posts", PostController, "index")
    router.get("/cms/posts/{id}", PostController, "show")
    router.post("/cms/posts", PostController, "store")
    router.get("/cms/pages", PageController, "index")
    router.get("/cms/media", MediaController, "index")

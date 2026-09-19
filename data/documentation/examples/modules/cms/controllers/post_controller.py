"""Thin HTTP Controller for Blog Posts in CMS Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse, Response

from ..schemas.cms_schema import CreatePostData
from ..services.cms_service import CmsService


class PostController(Controller):
    """HTTP transport controller for CMS blog post management (< 100 lines)."""

    def __init__(self, service: CmsService = None):
        self.service = service or CmsService()

    def index(self, request):
        """List blog posts and render index view or JSON."""
        posts = self.service.list_posts()
        if request.expects_json():
            return JsonResponse([p.to_dict() for p in posts])
        return self.view("cms::posts_index", {"posts": posts})

    def show(self, request, id):
        """Display a single post by public identifier."""
        post = self.service.get_post(id)
        if not post:
            return Response("Post not found", status=404)
        if request.expects_json():
            return JsonResponse(post.to_dict())
        return self.view("cms::posts_show", {"post": post})

    def store(self, request):
        """Handle post creation and return SEO-optimized result."""
        data = CreatePostData(
            title=request.input("title", ""),
            body=request.input("body", ""),
            user_id=int(request.input("user_id", 1)),
        )
        result = self.service.create_post(data)
        if request.expects_json():
            return JsonResponse(
                {
                    "post": result["post"].to_dict(),
                    "seo_analysis": result["seo_analysis"],
                },
                status=201,
            )
        return self.view("cms::posts_show", {"post": result["post"]})

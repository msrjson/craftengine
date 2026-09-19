"""Thin HTTP Controller for Static Pages in CMS Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse, Response

from ..services.cms_service import CmsService


class PageController(Controller):
    """HTTP transport controller for CMS static page management (< 100 lines)."""

    def __init__(self, service: CmsService = None):
        self.service = service or CmsService()

    def index(self, request):
        """Render pages dashboard view or JSON list."""
        if request.expects_json():
            return JsonResponse({"pages": []})
        return self.view("cms::pages_index", {"pages": []})

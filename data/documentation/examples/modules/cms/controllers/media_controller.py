"""Thin HTTP Controller for Media Library in CMS Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse

from ..services.cms_service import CmsService


class MediaController(Controller):
    """HTTP transport controller for CMS media management (< 100 lines)."""

    def __init__(self, service: CmsService = None):
        self.service = service or CmsService()

    def index(self, request):
        """List media library assets."""
        media = self.service.repository.get_all_media()
        if request.expects_json():
            return JsonResponse([m.to_dict() for m in media])
        return self.view("cms::media_index", {"media": media})

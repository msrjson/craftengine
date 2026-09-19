"""CMS Business Module — Native Module Lifecycle Bootstrap."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .repositories.cms_repository import CmsRepository
from .routes import register_routes
from .services.cms_service import CmsService

MODULE = {
    "slug": "cms",
    "name": "Content Management System",
    "version": "1.0.0",
    "description": "CMS domain module for managing blog posts, pages, and media assets.",
}


def register(app):
    """Register CMS domain services into the IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("module.cms.repository", lambda c: CmsRepository())
        container.singleton(
            "module.cms.service",
            lambda c: CmsService(repository=c.make("module.cms.repository")),
        )


def boot(app):
    """Boot runtime configuration and mount CMS module HTTP routes."""
    router = getattr(app, "router", None)
    if router:
        register_routes(router)

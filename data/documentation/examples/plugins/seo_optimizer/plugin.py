"""SEO Optimizer Plugin — Native Capability Plugin Descriptor."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .engine import SeoOptimizerEngine

PLUGIN = {
    "slug": "seo_optimizer",
    "name": "SEO Optimizer Plugin",
    "version": "1.0.0",
    "description": "Stateless SEO slugification, SERP analysis, and content optimizer plugin.",
}


def register(app):
    """Bind the SeoOptimizerEngine into the application IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("plugin.seo_optimizer", lambda c: SeoOptimizerEngine())

"""View configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

#: Slug of the active theme extension; empty renders without a theme. An
#: application choosing a theme per request (per tenant, per brand) registers a
#: resolver with `View.set_theme_resolver` instead (documentation/extensions.md).
theme = env("VIEW_THEME", "")

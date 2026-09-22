"""Authentication configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

defaults = {
    "guard": "web",
}

guards = {
    "web": {
        "driver": "session",
        "provider": "users",
    },
    "api": {
        "driver": "token",
        "provider": "users",
        "token_name": "api_token",
    },
}

providers = {
    "users": {
        "model": "app.Models.User.User",
    },
}

# The identity models this project provides. The engine resolves these through
# `engine/auth/registry.py` instead of importing `app.Models.*` directly, so a
# project is free to name, move or omit them: the RBAC console commands simply
# do not register when their model is absent.
#
# `user` is what the `users` provider above points at, repeated here because
# the provider answers "which model backs this guard" while this answers "which
# model is this project's user". They are the same class in a normal project
# and are allowed to diverge in one that runs several guards.
models = {
    "user": "app.Models.User.User",
    "role": "app.Models.Role.Role",
    "permission": "app.Models.Permission.Permission",
    "group": "app.Models.Group.Group",
}

# NOTE: no `password_timeout` here. It described a confirm-password window
# that Craft does not implement, and nothing read it - a knob with no wiring.


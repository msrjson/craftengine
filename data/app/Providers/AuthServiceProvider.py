"""Auth service provider — where the application registers its policies and
Gate abilities.

Anything the `Gate` facade can answer is declared here (or in a policy class
this file registers). The Gate denies by default, so an ability that is never
defined and matches no permission slug is a refusal, not an accident waiting to
be discovered.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Gate
from craft.providers import ServiceProvider


class AuthServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        Gate.define("is-admin", lambda user: user is not None and user.get_attribute("is_admin"))

        # Second control on the admin dashboard, which lists every user,
        # administrator and tenant. The route already declares `role:admin`;
        # this ability lets the controller assert the same thing itself, so a
        # single forgotten alias on a route cannot expose the directory.
        # `is_admin` OR the `admin` role — either is sufficient, so an
        # installation that manages access purely through roles and one that
        # flags the column both work.
        Gate.define(
            "access-admin-dashboard",
            lambda user: (
                user is not None
                and (
                    bool(user.get_attribute("is_admin"))
                    or (callable(getattr(user, "has_role", None)) and user.has_role("admin"))
                )
            ),
        )

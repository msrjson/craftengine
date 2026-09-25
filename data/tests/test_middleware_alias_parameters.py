"""Route middleware aliases: parameters are declared, typed and checked at boot."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.http import middleware as mw
from craft.http.kernel import MiddlewareAliasError


@pytest.fixture
def kernel(migrated_database):
    from craft.http.kernel import Kernel

    return Kernel(migrated_database)


class TestTypedParameters:
    def test_throttle_values_become_integers(self, kernel):
        (throttle,) = kernel.resolve_route_middleware(["throttle:30,120"])
        assert (throttle.max_attempts, throttle.decay_seconds) == (30, 120)

    def test_throttle_accepts_a_single_value(self, kernel):
        (throttle,) = kernel.resolve_route_middleware(["throttle:5"])
        assert (throttle.max_attempts, throttle.decay_seconds) == (5, 60)

    def test_a_non_integer_throttle_is_refused(self, kernel):
        with pytest.raises(MiddlewareAliasError, match="must be an integer"):
            kernel.resolve_route_middleware(["throttle:many"])

    def test_role_receives_its_slug(self, kernel):
        (role,) = kernel.resolve_route_middleware(["role:admin"])
        assert isinstance(role, mw.RequireRole)
        assert role.role == "admin"


class TestRefusedParameters:
    @pytest.mark.parametrize("entry", ["auth:api", "session:x", "csrf:x", "api:x", "firewall:x"])
    def test_an_alias_without_parameters_refuses_one(self, kernel, entry):
        with pytest.raises(MiddlewareAliasError, match="takes no route parameter"):
            kernel.resolve_route_middleware([entry])

    def test_auth_api_points_at_the_api_alias(self, kernel):
        with pytest.raises(MiddlewareAliasError, match="the api alias, not auth:api"):
            kernel.resolve_route_middleware(["auth:api"])

    def test_a_list_of_roles_is_refused_instead_of_denying_everyone(self, kernel):
        with pytest.raises(MiddlewareAliasError, match="takes 1 route parameter"):
            kernel.resolve_route_middleware(["role:admin,editor"])

    def test_the_error_is_still_a_key_error(self, kernel):
        with pytest.raises(KeyError):
            kernel.resolve_route_middleware(["auth:api"])


class TestUndeclaredMiddleware:
    def test_a_project_middleware_keeps_the_legacy_rule(self, kernel):
        class Tagged(mw.Middleware):
            def __init__(self, tag: str = "", app=None):
                self.tag = tag

        kernel.alias_middleware("tagged", Tagged)
        (tagged,) = kernel.resolve_route_middleware(["tagged:blue"])
        assert tagged.tag == "blue"

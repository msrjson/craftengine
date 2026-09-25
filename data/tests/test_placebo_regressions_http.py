"""Third round of placebo regressions — routing and validation.

Same theme as the other two files: promises the framework made and did not
keep. These were the last three found by a full sweep.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest


class TestNamedRoutesFailLoudly:
    """`url_for()` returned the literal `/{name}` for an unknown route, so a
    typo rendered a dead link and nobody found out until a human clicked."""

    def test_an_unknown_route_name_raises(self, migrated_database):
        from craft.container.application import Container

        router = Container.getInstance().make("router")
        with pytest.raises(KeyError):
            router.url_for("definitely.not.a.route")

    def test_the_view_helper_does_not_swallow_it(self, migrated_database):
        """The template helper caught everything and returned `"/"`, turning a
        mistyped route name into a link to the homepage."""
        from craft.view.forge import route_url

        with pytest.raises(Exception):
            route_url("definitely.not.a.route")

    def test_a_known_route_still_resolves(self, migrated_database):
        from craft.container.application import Container
        from craft.facades import Route

        Route.get("/t/placebo/named", lambda request: "ok").name("t.placebo.named")

        router = Container.getInstance().make("router")
        assert router.url_for("t.placebo.named") == "/t/placebo/named"


class TestUniqueAndExistsFailClosed:
    """Both rules wrapped their query in `except Exception: return`, so any
    database error made the rule *pass*: `unique:userz,email` validated
    cleanly and the duplicate was inserted."""

    # `Validator` runs the rules in its constructor, so a rule that now fails
    # loudly surfaces there rather than in `passes()`.

    def test_unique_against_a_missing_table_raises_instead_of_passing(
        self, migrated_database
    ):
        from craft.validation.validator import Validator

        with pytest.raises(Exception):
            Validator(
                {"email": "someone@craft.local"},
                {"email": "unique:table_that_does_not_exist,email"},
            )

    def test_exists_against_a_missing_table_raises_instead_of_passing(
        self, migrated_database
    ):
        from craft.validation.validator import Validator

        with pytest.raises(Exception):
            Validator(
                {"role_id": 1}, {"role_id": "exists:table_that_does_not_exist,id"}
            )

    def test_a_table_name_that_is_not_an_identifier_is_rejected(
        self, migrated_database
    ):
        """The table and column arguments are interpolated into SQL."""
        from craft.validation.validator import Validator

        with pytest.raises(ValueError):
            Validator(
                {"email": "x"}, {"email": "unique:users; DROP TABLE users --,email"}  # nr02: hostile payload, rejected before any SQL runs
            )

    def test_unique_still_works_against_a_real_table(self, migrated_database):
        from tests.support.models import User
        from craft.validation.validator import Validator

        suffix = uuid.uuid4().hex[:8]
        taken_email, free_email = f"dup_{suffix}@craft.local", f"free_{suffix}@craft.local"
        User.force_create({"name": "Dup", "email": taken_email, "password": "s3cret"})

        taken = Validator({"email": taken_email}, {"email": "unique:users,email"})
        assert taken.passes() is False

        free = Validator({"email": free_email}, {"email": "unique:users,email"})
        assert free.passes() is True

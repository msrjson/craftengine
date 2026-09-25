"""Group membership and attribute conditions on grants (RBAC + ABAC).

Authorization used to be able to say only *who you are*: a user held roles, and
roles held permissions. Two things were missing, and both are here:

* **Groups** — access granted to a team, so onboarding is one membership row
  rather than a tour of every role that team needs.
* **Conditions** — a permission is often not absolute (*edit articles, but only
  your own*; *approve invoices, but only under 10k*). Those are attributes of
  the resource and the acting user, not of the role.

The tests below check the four grant paths, both answers a conditional grant
can give, and the deliberate asymmetry between `has_permission()` (no resource,
so unconditional grants only) and `can(slug, resource)`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.auth.conditions import ConditionError, dump, matches, parse
from craft.facades import DB


@pytest.fixture
def rbac(migrated_database):
    """A user, a group, a role and two permissions, wired by the test itself.

    Nothing is deleted between tests (NR-02) and `roles.name`, `roles.slug`
    and the group and permission slugs are unique, so every name here carries
    a suffix of this test's own. A fresh user holds no grant but the ones the
    test writes, which keeps the assertions scoped to this test's rows.
    """
    from tests.support.models import Group, Permission, Role, User

    suffix = uuid.uuid4().hex[:8]
    slugs = {
        "group": f"content-team-{suffix}", "role": f"editor-{suffix}",
        "edit": f"edit-articles-{suffix}", "publish": f"publish-articles-{suffix}",
    }
    user = User.create({"name": "Ana", "email": f"ana-{suffix}@abac.local", "password": "s3cret"})
    other = User.create({"name": "Bo", "email": f"bo-{suffix}@abac.local", "password": "s3cret"})
    group = Group.create({"name": slugs["group"], "slug": slugs["group"]})
    role = Role.create({"name": slugs["role"], "slug": slugs["role"]})
    edit = Permission.create({"name": slugs["edit"], "slug": slugs["edit"]})
    publish = Permission.create({"name": slugs["publish"], "slug": slugs["publish"]})

    return {
        "user": user, "other": other, "group": group, "role": role,
        "edit": edit, "publish": publish, "slugs": slugs,
        "access": migrated_database.make("access"),
    }


def _id(model):
    return model.get_attribute("id")


def join(table, **columns):
    names = ", ".join(columns)
    placeholders = ", ".join(f":{name}" for name in columns)
    DB.statement(f"INSERT INTO {table} ({names}) VALUES ({placeholders})", columns)


class Article:
    """A stand-in resource: conditions are evaluated against plain attributes."""

    def __init__(self, **attributes):
        self._attributes = attributes

    def get_attribute(self, name):
        return self._attributes.get(name)


class TestTheFourGrantPaths:
    """A permission can reach a user four ways. All of them must count."""

    def test_direct_grant_to_the_user(self, rbac):
        join("permission_user", permission_id=_id(rbac["edit"]), user_id=_id(rbac["user"]))
        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is True
        assert rbac["other"].has_permission(rbac["slugs"]["edit"]) is False

    def test_through_a_role(self, rbac):
        join("role_user", user_id=_id(rbac["user"]), role_id=_id(rbac["role"]))
        join("permission_role", role_id=_id(rbac["role"]), permission_id=_id(rbac["edit"]))
        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is True

    def test_through_a_group_that_grants_a_role(self, rbac):
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join("group_role", group_id=_id(rbac["group"]), role_id=_id(rbac["role"]))
        join("permission_role", role_id=_id(rbac["role"]), permission_id=_id(rbac["edit"]))

        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is True
        # And the role itself is held, which is what `role:` middleware asks.
        assert rbac["user"].has_role(rbac["slugs"]["role"]) is True

    def test_through_a_group_that_grants_the_permission_directly(self, rbac):
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join("permission_group", group_id=_id(rbac["group"]), permission_id=_id(rbac["edit"]))
        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is True

    def test_a_user_outside_the_group_gets_nothing(self, rbac):
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join("permission_group", group_id=_id(rbac["group"]), permission_id=_id(rbac["edit"]))

        assert rbac["other"].has_permission(rbac["slugs"]["edit"]) is False
        assert rbac["other"].in_group(rbac["slugs"]["group"]) is False
        assert rbac["user"].in_group(rbac["slugs"]["group"]) is True


class TestConditionalGrants:
    """The ABAC half: a grant narrowed by attributes of the resource."""

    def test_ownership_condition_allows_only_your_own(self, rbac):
        join(
            "permission_user",
            permission_id=_id(rbac["edit"]),
            user_id=_id(rbac["user"]),
            conditions=dump({"user_id": "@user.id"}),
        )

        mine = Article(user_id=_id(rbac["user"]))
        theirs = Article(user_id=_id(rbac["other"]))

        assert rbac["user"].can(rbac["slugs"]["edit"], mine) is True
        assert rbac["user"].can(rbac["slugs"]["edit"], theirs) is False

    def test_a_conditional_grant_does_not_answer_the_unconditional_question(self, rbac):
        """`has_permission()` is asked with no resource in hand.

        Saying True there would hand out the unconditional version of a grant
        that was deliberately narrowed — the escalation this asymmetry exists
        to prevent.
        """
        join(
            "permission_user",
            permission_id=_id(rbac["edit"]),
            user_id=_id(rbac["user"]),
            conditions=dump({"user_id": "@user.id"}),
        )

        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is False
        assert rbac["user"].can(rbac["slugs"]["edit"], Article(user_id=_id(rbac["user"]))) is True

    def test_grants_add_up_rather_than_veto_each_other(self, rbac):
        """One narrow grant and one broad grant means the broad one wins."""
        join(
            "permission_user",
            permission_id=_id(rbac["edit"]),
            user_id=_id(rbac["user"]),
            conditions=dump({"user_id": "@user.id"}),
        )
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join("permission_group", group_id=_id(rbac["group"]), permission_id=_id(rbac["edit"]))

        assert rbac["user"].can(rbac["slugs"]["edit"], Article(user_id=_id(rbac["other"]))) is True
        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is True

    def test_a_ceiling_condition(self, rbac):
        join(
            "permission_group",
            permission_id=_id(rbac["publish"]),
            group_id=_id(rbac["group"]),
            conditions=dump({"amount": {"lte": 10000}}),
        )
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))

        assert rbac["user"].can(rbac["slugs"]["publish"], Article(amount=9999)) is True
        assert rbac["user"].can(rbac["slugs"]["publish"], Article(amount=10001)) is False

    def test_a_broken_condition_denies_instead_of_allowing(self, rbac):
        """A typo in stored conditions must not become an open grant."""
        DB.statement(
            "INSERT INTO permission_user (permission_id, user_id, conditions) "
            "VALUES (:p, :u, :c)",
            {"p": _id(rbac["edit"]), "u": _id(rbac["user"]), "c": "{not json at all"},
        )
        assert rbac["user"].can(rbac["slugs"]["edit"], Article(user_id=_id(rbac["user"]))) is False
        assert rbac["user"].has_permission(rbac["slugs"]["edit"]) is False


class TestGateUsesTheGrants:
    def test_gate_evaluates_conditions_against_the_resource(self, rbac, migrated_database):
        join(
            "permission_user",
            permission_id=_id(rbac["edit"]),
            user_id=_id(rbac["user"]),
            conditions=dump({"user_id": "@user.id"}),
        )
        gate = migrated_database.make("gate")

        assert gate.allows(rbac["slugs"]["edit"], rbac["user"], Article(user_id=_id(rbac["user"]))) is True
        assert gate.allows(rbac["slugs"]["edit"], rbac["user"], Article(user_id=_id(rbac["other"]))) is False

    def test_gate_still_denies_an_unknown_ability(self, rbac, migrated_database):
        gate = migrated_database.make("gate")
        assert gate.allows("nobody-defined-this", rbac["user"]) is False


class TestExplain:
    def test_explain_names_every_path_and_its_conditions(self, rbac):
        join("permission_user", permission_id=_id(rbac["edit"]), user_id=_id(rbac["user"]))
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join(
            "permission_group",
            permission_id=_id(rbac["edit"]),
            group_id=_id(rbac["group"]),
            conditions=dump({"user_id": "@user.id"}),
        )

        sources = {g["source"] for g in rbac["access"].explain(rbac["user"], rbac["slugs"]["edit"])}
        assert sources == {"direct", "group"}

    def test_listings_report_groups_roles_and_permissions(self, rbac):
        join("group_user", user_id=_id(rbac["user"]), group_id=_id(rbac["group"]))
        join("group_role", group_id=_id(rbac["group"]), role_id=_id(rbac["role"]))
        join("permission_role", role_id=_id(rbac["role"]), permission_id=_id(rbac["edit"]))

        access = rbac["access"]
        assert access.groups(rbac["user"]) == [rbac["slugs"]["group"]]
        assert access.roles(rbac["user"]) == [rbac["slugs"]["role"]]
        assert access.permissions(rbac["user"]) == [rbac["slugs"]["edit"]]


class TestConditionLanguage:
    """The predicate vocabulary itself, away from the database."""

    class User:
        def __init__(self, **attributes):
            self._attributes = attributes

        def get_attribute(self, name):
            return self._attributes.get(name)

    def test_none_is_unconditional(self):
        assert matches(None, self.User(id=1), None) is True

    def test_an_empty_object_denies(self):
        """`{}` is someone meaning something; guessing "allow" is the wrong way
        to be wrong."""
        assert matches({}, self.User(id=1), Article()) is False

    def test_conditions_without_a_resource_deny(self):
        assert matches({"user_id": "@user.id"}, self.User(id=1), None) is False

    def test_every_key_must_hold(self):
        user = self.User(id=1)
        resource = Article(user_id=1, status="draft")
        assert matches({"user_id": "@user.id", "status": "draft"}, user, resource) is True
        assert matches({"user_id": "@user.id", "status": "live"}, user, resource) is False

    @pytest.mark.parametrize(
        "condition,expected",
        [
            ({"status": {"in": ["draft", "review"]}}, True),
            ({"status": {"not_in": ["draft"]}}, False),
            ({"status": {"ne": "live"}}, True),
            ({"views": {"gt": 10}}, True),
            ({"views": {"lt": 10}}, False),
            ({"views": {"gte": 42}}, True),
            ({"views": {"lte": 41}}, False),
            ({"archived_at": {"is_null": True}}, True),
            ({"title": {"contains": "eng"}}, True),
        ],
    )
    def test_operators(self, condition, expected):
        resource = Article(status="draft", views=42, archived_at=None, title="engine")
        assert matches(condition, self.User(id=1), resource) is expected

    def test_ids_compare_across_driver_types(self):
        """SQLite hands back int, another driver may hand back str; ownership
        must not depend on which."""
        assert matches({"user_id": "@user.id"}, self.User(id=7), Article(user_id="7")) is True

    def test_an_unknown_operator_raises_rather_than_passing(self):
        with pytest.raises(ConditionError):
            matches({"views": {"approximately": 42}}, self.User(id=1), Article(views=42))

    def test_parse_rejects_non_objects(self):
        assert parse(None) is None
        assert parse("") is None
        assert parse('{"a": 1}') == {"a": 1}
        with pytest.raises(ConditionError):
            parse("[1, 2]")
        with pytest.raises(ConditionError):
            parse("{oops")

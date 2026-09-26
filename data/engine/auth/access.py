"""
AccessResolver — the one place that answers "can this user do this?".
Category: Core Framework (Auth).
Relations:
  - Bound in the container as `access`; used by `GateManager.allows()`
    (`engine/auth/gate.py`), by the `role:`/`permission:`/`group:` route
    middleware (`engine/http/middleware.py`), and by `app/Models/User.py`,
    which delegates `has_role`/`has_permission`/`can` here.
  - Reads the RBAC tables created by
    `database/migrations/2025_01_01_000004_create_framework_dynamic_tables.py`
    and the group/ABAC tables added by
    `database/migrations/2026_08_11_000001_create_groups_and_abac_tables.py`.
  - Evaluates grant conditions through `engine/auth/conditions.py`.
References:
  - Guide: `documentation/authorization.md`

Why one resolver instead of a method on the model: a permission can reach a
user by four different paths, and every caller that re-implements "check the
role table" gets one of them wrong. Keeping the union in a single query means
adding a fifth path later changes one file, not five.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

from engine.auth.conditions import matches_safely

_LOG = logging.getLogger("craft")

_request_access_cache: ContextVar[Optional[Dict[str, Any]]] = ContextVar("_request_access_cache", default=None)


def get_access_cache() -> Dict[str, Any]:
    cache = _request_access_cache.get()
    if cache is None:
        cache = {}
        _request_access_cache.set(cache)
    return cache


def clear_access_cache() -> None:
    """Clear request-scoped access and permission resolution cache."""
    _request_access_cache.set(None)

#: Every route by which a permission slug can reach a user, unioned into one
#: query. `source` is carried through purely so a human (or an audit screen)
#: can answer "why does this person have this?" without running four queries.
_PERMISSION_SQL = """
SELECT 'direct' AS source, pu.conditions AS conditions
  FROM permissions p
  JOIN permission_user pu ON pu.permission_id = p.id
 WHERE pu.user_id = :user AND p.slug = :slug

UNION ALL

SELECT 'role' AS source, pr.conditions AS conditions
  FROM permissions p
  JOIN permission_role pr ON pr.permission_id = p.id
  JOIN role_user ru ON ru.role_id = pr.role_id
 WHERE ru.user_id = :user AND p.slug = :slug

UNION ALL

SELECT 'group-role' AS source, pr.conditions AS conditions
  FROM permissions p
  JOIN permission_role pr ON pr.permission_id = p.id
  JOIN group_role gr ON gr.role_id = pr.role_id
  JOIN group_user gu ON gu.group_id = gr.group_id
 WHERE gu.user_id = :user AND p.slug = :slug

UNION ALL

SELECT 'group' AS source, pg.conditions AS conditions
  FROM permissions p
  JOIN permission_group pg ON pg.permission_id = p.id
  JOIN group_user gu ON gu.group_id = pg.group_id
 WHERE gu.user_id = :user AND p.slug = :slug
"""

#: Roles held directly, plus roles inherited from a group.
_ROLE_SQL = """
SELECT r.slug AS slug, ru.conditions AS conditions
  FROM roles r
  JOIN role_user ru ON ru.role_id = r.id
 WHERE ru.user_id = :user

UNION ALL

SELECT r.slug AS slug, gr.conditions AS conditions
  FROM roles r
  JOIN group_role gr ON gr.role_id = r.id
  JOIN group_user gu ON gu.group_id = gr.group_id
 WHERE gu.user_id = :user
"""

_GROUP_SQL = """
SELECT g.slug AS slug
  FROM groups g
  JOIN group_user gu ON gu.group_id = g.id
 WHERE gu.user_id = :user
"""

#: All permission slugs a user can hold, by any path. Used for listings and
#: audit screens, never for a yes/no decision — those go through `allows()`,
#: which evaluates conditions.
_ALL_PERMISSIONS_SQL = """
SELECT p.slug AS slug, pu.conditions AS conditions
  FROM permissions p JOIN permission_user pu ON pu.permission_id = p.id
 WHERE pu.user_id = :user
UNION ALL
SELECT p.slug AS slug, pr.conditions AS conditions
  FROM permissions p
  JOIN permission_role pr ON pr.permission_id = p.id
  JOIN role_user ru ON ru.role_id = pr.role_id
 WHERE ru.user_id = :user
UNION ALL
SELECT p.slug AS slug, pr.conditions AS conditions
  FROM permissions p
  JOIN permission_role pr ON pr.permission_id = p.id
  JOIN group_role gr ON gr.role_id = pr.role_id
  JOIN group_user gu ON gu.group_id = gr.group_id
 WHERE gu.user_id = :user
UNION ALL
SELECT p.slug AS slug, pg.conditions AS conditions
  FROM permissions p
  JOIN permission_group pg ON pg.permission_id = p.id
  JOIN group_user gu ON gu.group_id = pg.group_id
 WHERE gu.user_id = :user
"""


def _user_id(user: Any) -> Any:
    if user is None:
        return None
    getter = getattr(user, "get_attribute", None)
    if callable(getter):
        return getter("id")
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)


class AccessResolver:
    """Resolves roles, groups and permissions — including their conditions."""

    def __init__(self, app: Any = None):
        self.app = app

    # -- plumbing --------------------------------------------------------------

    def _db(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("db")
            except Exception:
                pass
        from craft.facades import DB

        return DB

    def _rows(self, sql: str, user_id: Any) -> List[Any]:
        """Run a resolution query.

        A failure here is a denial, never an allow, and it is logged loudly:
        an authorization check that cannot reach its tables has not decided
        anything, and guessing "yes" is the one answer that can never be
        corrected after the fact.
        """
        cache = get_access_cache()
        cache_key = f"rows:{user_id}:{hash(sql)}"
        if cache_key in cache:
            return cache[cache_key]

        try:
            res = self._db().statement(sql, {"user": user_id}, read=True).fetchall()
            cache[cache_key] = res
            return res
        except Exception:
            _LOG.error(
                "Authorization query failed; denying. This is not a permission "
                "decision — the tables could not be read.", exc_info=True,
            )
            return []

    # -- grants ----------------------------------------------------------------

    def grants(self, user: Any, slug: str) -> List[Dict[str, Any]]:
        """Every grant of `slug` reaching this user, with its raw conditions.

        Returns a list of `{"source": ..., "conditions": ...}` — empty means the
        user has no path to this permission at all.
        """
        user_id = _user_id(user)
        if user_id is None or not slug:
            return []
        return self._grants(user_id, slug)

    def _grants(self, user_id: Any, slug: str) -> List[Dict[str, Any]]:
        cache = get_access_cache()
        cache_key = f"grants:{user_id}:{slug}"
        if cache_key in cache:
            return cache[cache_key]

        try:
            rows = (
                self._db()
                .statement(_PERMISSION_SQL, {"user": user_id, "slug": slug}, read=True)
                .fetchall()
            )
        except Exception:
            _LOG.error(
                "Authorization query failed for permission %r; denying.", slug,
                exc_info=True,
            )
            return []
        res = [{"source": row["source"], "conditions": row["conditions"]} for row in rows]
        cache[cache_key] = res
        return res

    # -- questions -------------------------------------------------------------

    def has_permission(self, user: Any, slug: str) -> bool:
        """Whether the user holds `slug` **unconditionally**.

        Conditional grants are excluded on purpose. This method is asked
        without a resource — "can they edit articles?" — and a grant that says
        *only their own* has not answered that question. Answering True would
        widen a deliberately narrowed grant; ask `allows(user, slug, resource)`
        instead when there is a resource in hand.
        """
        user_id = _user_id(user)
        if user_id is None or not slug:
            return False
        for grant in self._grants(user_id, slug):
            if grant["conditions"] in (None, ""):
                return True
        return False

    def allows(self, user: Any, slug: str, resource: Any = None) -> bool:
        """Whether the user may do `slug`, optionally to a specific resource.

        Any single matching grant is enough — grants add up, they do not veto
        each other. An unconditional grant allows outright; a conditional one
        allows when its conditions hold for this resource.
        """
        user_id = _user_id(user)
        if user_id is None or not slug:
            return False
        for grant in self._grants(user_id, slug):
            raw = grant["conditions"]
            if raw in (None, ""):
                return True
            if matches_safely(raw, user, resource):
                return True
        return False

    def has_role(self, user: Any, slug: str) -> bool:
        """Whether the user holds a role directly or through a group."""
        user_id = _user_id(user)
        if user_id is None or not slug:
            return False
        return any(row["slug"] == slug for row in self._rows(_ROLE_SQL, user_id))

    def in_group(self, user: Any, slug: str) -> bool:
        user_id = _user_id(user)
        if user_id is None or not slug:
            return False
        return any(row["slug"] == slug for row in self._rows(_GROUP_SQL, user_id))

    # -- listings (audit screens, CLI, debugging) ------------------------------

    def roles(self, user: Any) -> List[str]:
        rows = self._rows(_ROLE_SQL, _user_id(user))
        return sorted({row["slug"] for row in rows})

    def groups(self, user: Any) -> List[str]:
        rows = self._rows(_GROUP_SQL, _user_id(user))
        return sorted({row["slug"] for row in rows})

    def permissions(self, user: Any) -> List[str]:
        """Every permission slug reachable by this user, conditional included.

        For display. A slug appearing here does not mean the user may act on a
        given resource — that is what `allows()` is for.
        """
        rows = self._rows(_ALL_PERMISSIONS_SQL, _user_id(user))
        return sorted({row["slug"] for row in rows})

    def explain(self, user: Any, slug: str) -> List[Dict[str, Any]]:
        """Why the user does (or does not) hold `slug` — for audit screens.

        Each entry names the path (`direct`, `role`, `group-role`, `group`) and
        the conditions attached to it, so "why can this person do that?" has an
        answer that does not require reading five tables by hand.
        """
        return self._grants(_user_id(user), slug)


__all__ = ["AccessResolver", "clear_access_cache", "get_access_cache"]

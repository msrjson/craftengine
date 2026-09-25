"""Behaviour shared by the identity models a project provides.

The engine ships authentication but not the models it authenticates: a project
declares its own `User` and points `config/auth.py` at it, and
`engine/auth/registry.py` resolves it. That leaves one problem worth solving
here rather than in every generated project - password hashing must happen on
every write path, and getting it wrong stores plaintext.

`AuthenticatableMixin` carries that guarantee. A generated `User` is a handful
of lines because the part that must not be reimplemented lives here.
"""

from __future__ import annotations

from typing import Any, Dict, List

from engine.auth.password import Hash


class AuthenticatableMixin:
    """Password handling for a model used as an authentication subject.

    Mix it into a model that stores a hashed secret in a `password` column:

        class User(AuthenticatableMixin, Model):
            __table__ = "users"
            fillable = ["name", "email", "password"]
            hidden = ["password", "remember_token"]

    The hook is on `force_create` rather than `create` deliberately. `create`
    funnels through `force_create` after mass-assignment filtering, so hashing
    here covers both, including the trusted paths that bypass the guard -
    seeders, and admin actions that set fields `fillable` refuses.
    """

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> Any:
        """Persist a record, hashing the password on the way in.

        Args:
            attributes: Column values. A `password` that is not already hashed
                is hashed before it reaches the database.

        Returns:
            The created model instance.
        """
        attributes = dict(attributes)
        password = attributes.get("password")
        if password and not Hash.is_hashed(password):
            attributes["password"] = Hash.make(password)
        return super().force_create(attributes)  # type: ignore[misc]

    def save(self) -> Any:
        """Persist the record, hashing a changed plaintext password first.

        `force_create` covers inserts; this covers updates, through `save()`,
        `update()`, `update_attributes()` and `user.password = ...`, which
        otherwise wrote the plaintext straight to the column.

        Returns:
            This model.
        """
        password = self.get_attribute("password")  # type: ignore[attr-defined]
        if password and not Hash.is_hashed(password):
            self._attributes["password"] = Hash.make(password)  # type: ignore[attr-defined]
        return super().save()  # type: ignore[misc]

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash.

        Args:
            password: The candidate password, in plaintext.

        Returns:
            True when the password matches.
        """
        return Hash.check(password, self.get_attribute("password"))  # type: ignore[attr-defined]


def _access_resolver() -> Any:
    """Return the container's AccessResolver, or None outside a booted app.

    Models are used in unit tests with no application booted, so every caller
    of this has to degrade - and the only safe direction is denial, never a
    grant.

    Returns:
        The `access` binding, or None when no application is available.
    """
    from engine.container.application import Container

    try:
        return Container.getInstance().make("access")
    except (LookupError, AttributeError, RuntimeError):
        return None


def _related_model(kind: str) -> Any:
    """Resolve the project's `role` or `group` model through the registry.

    Args:
        kind: `role` or `group`.

    Returns:
        The configured model class.
    """
    from engine.auth import registry

    return registry.model_for(kind, _access_config())


def _access_config() -> Any:
    """Return the configuration repository of the booted application.

    Returns:
        The `config` binding, or None outside a booted app.
    """
    from engine.container.application import Container

    try:
        return Container.getInstance().make("config")
    except (LookupError, AttributeError, RuntimeError):
        return None


class AuthorizableMixin:
    """Role, permission and group checks for an authenticated model.

    The engine's `role:`, `permission:` and `group:` route middleware and
    `Auth.can()` call these methods on the current user. Without them, the
    middleware raises `MisconfigurationError` naming this mixin. A generated `User` inherits them rather
    than reimplementing them, because a permission reaches a user by four
    paths - direct, through a role, through a group's role, through a group -
    and every hand-written check misses at least one.

    Every decision is delegated to `craft.auth.access.AccessResolver`. Outside a
    booted application each check answers False: a missing resolver must never
    read as permission.
    """

    def has_role(self, slug: str) -> bool:
        """Whether the user holds the role, directly or through a group.

        Args:
            slug: The role slug.

        Returns:
            True when the role is held.
        """
        access = _access_resolver()
        return bool(access is not None and access.has_role(self, slug))

    def has_permission(self, slug: str) -> bool:
        """Whether the user holds the permission unconditionally.

        Grants narrowed by attribute conditions are excluded: asked without a
        resource, a grant that says "only your own" has not answered. Use
        `can(slug, resource)` when there is a resource.

        Args:
            slug: The permission slug.

        Returns:
            True when an unconditional grant reaches the user.
        """
        access = _access_resolver()
        return bool(access is not None and access.has_permission(self, slug))

    def can(self, slug: str, resource: Any = None) -> bool:
        """Whether the user may do `slug`, optionally to a specific resource.

        Args:
            slug: The permission slug.
            resource: The record a conditional grant is evaluated against.

        Returns:
            True when some grant allows it.
        """
        access = _access_resolver()
        return bool(access is not None and access.allows(self, slug, resource))

    def in_group(self, slug: str) -> bool:
        """Whether the user is a member of the group.

        Args:
            slug: The group slug.

        Returns:
            True on membership.
        """
        access = _access_resolver()
        return bool(access is not None and access.in_group(self, slug))

    def permission_slugs(self) -> List[str]:
        """Every permission slug reachable by this user, for display and audit.

        Returns:
            The slugs, or an empty list outside a booted application.
        """
        access = _access_resolver()
        return list(access.permissions(self)) if access is not None else []

    def roles(self) -> Any:
        """Roles assigned to the user through the `role_user` pivot.

        Returns:
            The relationship.
        """
        from engine.orm.relationships import BelongsToMany

        return BelongsToMany(
            self, _related_model("role"), pivot_table="role_user",
            foreign_pivot_key="user_id", related_pivot_key="role_id", name="roles",
        )

    def groups(self) -> Any:
        """Groups the user belongs to through the `group_user` pivot.

        Returns:
            The relationship.
        """
        from engine.orm.relationships import BelongsToMany

        return BelongsToMany(
            self, _related_model("group"), pivot_table="group_user",
            foreign_pivot_key="user_id", related_pivot_key="group_id", name="groups",
        )

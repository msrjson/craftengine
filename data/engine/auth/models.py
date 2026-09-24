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

from typing import Any, Dict

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

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash.

        Args:
            password: The candidate password, in plaintext.

        Returns:
            True when the password matches.
        """
        return Hash.check(password, self.get_attribute("password"))  # type: ignore[attr-defined]

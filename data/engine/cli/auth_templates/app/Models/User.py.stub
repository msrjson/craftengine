"""The user this application authenticates."""

from craft.auth.models import AuthenticatableMixin, AuthorizableMixin
from craft.orm.model import Model


class User(AuthenticatableMixin, AuthorizableMixin, Model):
    """An account that can sign in.

    Add your own columns and relationships here; this model is yours.

    AuthenticatableMixin hashes the password on every insert path, so never
    store a plaintext secret by writing to the column directly.
    AuthorizableMixin answers has_role, has_permission and can, which the
    `role:` and `permission:` route middleware call on the signed-in user.
    """

    __table__ = "users"

    # Mass assignment is limited to what a registration form may set. Anything
    # that grants privilege stays out of this list and is set explicitly, on a
    # trusted path, or it becomes a privilege escalation through form input.
    fillable = ["name", "email", "password"]
    hidden = ["password", "remember_token"]

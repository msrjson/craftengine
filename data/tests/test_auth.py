"""Password hashing, authentication and the authorization gate."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.auth.gate import GateManager
from craft.auth.manager import AuthManager
from craft.auth.password import Hash
from craft.exceptions.handler import AuthorizationException


class TestHash:
    def test_hash_is_not_the_plaintext(self):
        assert Hash.make("secret") != "secret"

    def test_check_accepts_the_right_password(self):
        assert Hash.check("secret", Hash.make("secret")) is True

    def test_check_rejects_the_wrong_password(self):
        assert Hash.check("wrong", Hash.make("secret")) is False

    def test_hashes_are_salted_and_therefore_unique(self):
        assert Hash.make("secret") != Hash.make("secret")

    def test_check_against_none_is_false(self):
        assert Hash.check("secret", None) is False

    def test_check_against_plaintext_is_false(self):
        # A stored plaintext value must never authenticate.
        assert Hash.check("secret", "secret") is False

    def test_is_hashed_detects_framework_hashes(self):
        assert Hash.is_hashed(Hash.make("secret")) is True
        assert Hash.is_hashed("plaintext") is False
        assert Hash.is_hashed(None) is False

    def test_is_hashed_recognises_bcrypt_prefixes(self):
        assert Hash.is_hashed("$2b$12$abcdefghijklmnopqrstuv") is True

    def test_new_hashes_use_argon2id(self):
        assert Hash.make("secret").startswith("$argon2id$")

    def test_is_hashed_recognises_argon2_prefixes(self):
        assert Hash.is_hashed("$argon2id$v=19$m=19456,t=2,p=1$abc$def") is True

    def test_a_legacy_bcrypt_hash_still_verifies(self):
        import bcrypt

        # Real bcrypt hash, low cost (4) purely for test speed.
        bcrypt_hash = bcrypt.hashpw(b"legacy-secret", bcrypt.gensalt(rounds=4)).decode()
        assert Hash.check("legacy-secret", bcrypt_hash) is True
        assert Hash.check("wrong", bcrypt_hash) is False

    def test_a_legacy_pbkdf2_hash_still_verifies(self):
        # A hash this module itself would have produced before Argon2id existed.
        import base64
        import hashlib

        salt = b"0123456789abcdef"
        digest = hashlib.pbkdf2_hmac("sha256", b"legacy-secret", salt, 1000)
        legacy_hash = "$".join([
            "pbkdf2_sha256", "1000",
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ])
        assert Hash.check("legacy-secret", legacy_hash) is True
        assert Hash.check("wrong", legacy_hash) is False

    def test_needs_rehash_flags_a_legacy_hash_but_not_a_fresh_argon2id_one(self):
        assert Hash.needs_rehash("$2b$04$C6UzMDM.H6dfI/f/IKcEeOtRVpitmxVtDL7L4y1KRZI80B/pQzr5S") is True
        assert Hash.needs_rehash(Hash.make("secret")) is False
        assert Hash.needs_rehash(None) is True


class TestAuthManager:
    @pytest.fixture
    def auth(self, migrated_database):
        manager = AuthManager(migrated_database)
        manager.logout()
        return manager

    @pytest.fixture
    def user(self):
        import uuid

        from tests.support.models import User

        return User.create(
            {
                "name": "Auth Test",
                "email": f"auth-test-{uuid.uuid4().hex[:8]}@craft.local",
                "password": "correct-horse",
                "is_admin": False,
            }
        )

    def test_starts_as_a_guest(self, auth):
        assert auth.check() is False
        assert auth.guest() is True
        assert auth.user() is None

    def test_password_is_stored_hashed(self, user):
        assert user.get_attribute("password") != "correct-horse"
        assert Hash.is_hashed(user.get_attribute("password"))

    def test_attempt_succeeds_with_valid_credentials(self, auth, user):
        assert auth.attempt(
            {"email": user.get_attribute("email"), "password": "correct-horse"}
        ) is True
        assert auth.check() is True
        assert auth.user().get_attribute("email") == user.get_attribute("email")

    def test_attempt_fails_with_a_wrong_password(self, auth, user):
        assert auth.attempt(
            {"email": user.get_attribute("email"), "password": "nope"}
        ) is False
        assert auth.guest() is True

    def test_attempt_fails_for_an_unknown_user(self, auth, user):
        assert auth.attempt({"email": "ghost@craft.local", "password": "x"}) is False

    def test_attempt_without_a_password_fails(self, auth, user):
        assert auth.attempt({"email": user.get_attribute("email")}) is False

    def test_logout_clears_the_user(self, auth, user):
        auth.attempt({"email": user.get_attribute("email"), "password": "correct-horse"})
        auth.logout()
        assert auth.check() is False

    def test_login_using_id(self, auth, user):
        assert auth.login_using_id(user.get_attribute("id")) is not None
        assert auth.check() is True

    def test_once_authenticates_for_this_request(self, auth, user):
        """`once()` logs the user in for the current request.

        This previously asserted `guest() is True` afterwards, which pinned
        the bug rather than the contract: authenticating nobody makes `once()`
        an exact alias of `validate()` under a name that promises a login.
        """
        assert auth.once(
            {"email": user.get_attribute("email"), "password": "correct-horse"}
        ) is True
        assert auth.check() is True
        assert auth.user().get_attribute("email") == user.get_attribute("email")

    def test_once_does_not_persist_to_the_session(self, auth, user):
        """"Without persisting" is about the session, not about the request:
        nothing is written, so the login does not survive to the next one."""
        class RecordingSession:
            def __init__(self):
                self.writes = []

            def put(self, key, value):
                self.writes.append(key)

            def get(self, key, default=None):
                return default

            def forget(self, key):
                self.writes.append(("forget", key))

        session = RecordingSession()
        auth.set_session(session)
        auth.once({"email": user.get_attribute("email"), "password": "correct-horse"})

        assert session.writes == []

    def test_once_rejects_bad_credentials(self, auth, user):
        assert auth.once(
            {"email": user.get_attribute("email"), "password": "wrong"}
        ) is False
        assert auth.check() is False

    def test_check_password_on_the_model(self, user):
        assert user.check_password("correct-horse") is True
        assert user.check_password("wrong") is False

    def test_password_is_hidden_from_serialization(self, user):
        assert "password" not in user.to_dict()


class TestGate:
    @pytest.fixture
    def gate(self):
        return GateManager()

    def test_unknown_ability_is_denied_by_default(self, gate):
        assert gate.allows("anything", object()) is False

    def test_defined_ability_is_consulted(self, gate):
        gate.define("edit", lambda user: user == "owner")
        assert gate.allows("edit", "owner") is True
        assert gate.allows("edit", "stranger") is False

    def test_denies_is_the_inverse(self, gate):
        gate.define("edit", lambda user: True)
        assert gate.denies("edit", "anyone") is False

    def test_policy_is_used_for_the_model(self, gate):
        class Post:
            pass

        class PostPolicy:
            def update(self, user, post):
                return user == "author"

        gate.policy(Post, PostPolicy)
        assert gate.allows("update", "author", Post()) is True
        assert gate.allows("update", "reader", Post()) is False

    def test_authorize_raises_when_denied(self, gate):
        with pytest.raises(AuthorizationException):
            gate.authorize("missing", object())

    def test_authorize_is_silent_when_allowed(self, gate):
        gate.define("view", lambda user: True)
        gate.authorize("view", object())


class TestPasswordHashingOnUpdate:
    """A changed password is hashed on every write path, not only on insert."""

    @staticmethod
    def _user_class():
        from craft.auth.models import AuthenticatableMixin
        from craft.orm.model import Model

        class HashedUser(AuthenticatableMixin, Model):
            __table__ = "users"
            fillable = ["name", "email", "password"]

        return HashedUser

    def _create(self):
        import uuid

        return self._user_class().create({
            "name": "hash", "email": f"hash-{uuid.uuid4().hex}@craft.local", "password": "first-secret",
        })

    @pytest.mark.parametrize("write", ["assign", "update", "update_attributes"])
    def test_a_changed_password_is_stored_hashed(self, migrated_database, write):
        user = self._create()
        if write == "assign":
            user.password = "second-secret"
            user.save()
        else:
            getattr(user, write)({"password": "second-secret"})
        stored = type(user).find(user.get_attribute("id")).get_attribute("password")
        assert stored != "second-secret"
        assert Hash.check("second-secret", stored)

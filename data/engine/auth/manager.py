"""
AuthManager - Resolves, authenticates, and remembers the current user via the
session; login rotates the session id to close session fixation.
Category: Core Framework (Auth).
Relations:
  - Bound as `auth`, exposed via the `Auth` facade; rehydrated per request by
    the `Authenticate` middleware (`engine/http/middleware.py`).
  - Hashes/verifies passwords through `engine/auth/password.py`.
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import importlib
import threading
from typing import Any, Dict, Optional

from engine.auth import registry
from engine.auth.password import Hash


class AuthManager:
    """Resolves, authenticates and remembers the current user.

    The manager is a container singleton, but "the current user" and "the
    current session" belong to the request being served. Once requests are
    handled on a thread pool, two of them share this object - so that state is
    kept per-thread. Storing it on the instance would mean one visitor's
    request could observe, or overwrite, another visitor's identity.
    """

    def __init__(self, app: Any = None):
        self.app = app
        self._state = threading.local()

    # -- per-request state -----------------------------------------------------

    @property
    def _user(self) -> Optional[Any]:
        return getattr(self._state, "user", None)

    @_user.setter
    def _user(self, value: Optional[Any]) -> None:
        self._state.user = value

    @property
    def _session(self) -> Any:
        return getattr(self._state, "session", None)

    @_session.setter
    def _session(self, value: Any) -> None:
        self._state.session = value

    # -- provider resolution ---------------------------------------------------

    def _config(self) -> Any:
        if self.app is None:
            return None
        try:
            return self.app.make("config")
        except Exception:
            return None

    def provider_name(self, guard: Optional[str] = None) -> str:
        """Provider backing a guard - `auth.defaults.guard` when none is given.

        `auth.defaults.guard` and the `provider` key of each guard used to be
        decorative: the user model was read straight from
        `auth.providers.users.model`, so renaming the provider or pointing the
        default guard elsewhere changed nothing.
        """
        config = self._config()
        if config is None:
            return "users"
        guard = guard or config.get("auth.defaults.guard", "web") or "web"
        return config.get(f"auth.guards.{guard}.provider", "users") or "users"

    def user_model(self, guard: Optional[str] = None) -> Any:
        """Resolve the user model class of a guard's provider.

        The guard's own `provider.model` wins. When it names nothing, the
        project's `auth.models.user` answers instead.

        There is deliberately no hardcoded fallback. This used to default to
        `app.Models.User.User`, which silently required every project to
        reproduce the demo application's directory layout, and turned a
        missing configuration key into a confusing ImportError deep in a
        request instead of a named configuration failure.

        Args:
            guard: The guard to resolve for, or None for the default guard.

        Returns:
            The user model class.

        Raises:
            IdentityModelNotConfigured: If neither the guard's provider nor
                `auth.models.user` names an importable class.
        """
        config = self._config()
        path = None
        if config is not None:
            provider = self.provider_name(guard)
            path = config.get(f"auth.providers.{provider}.model")
        if not path:
            return registry.model_for("user", config)
        try:
            return registry._import_class(path)
        except (ImportError, AttributeError) as exc:
            raise registry.IdentityModelNotConfigured(
                "user", registry.REASON_IMPORT_FAILED, path=path, cause=str(exc)
            ) from exc

    # -- state -----------------------------------------------------------------

    def user(self) -> Optional[Any]:
        return self._user

    def id(self) -> Any:
        return self._user.get_attribute("id") if self._user is not None else None

    def check(self) -> bool:
        return self._user is not None

    def guest(self) -> bool:
        return self._user is None

    def login(self, user: Any) -> Any:
        """Authenticate a user and persist them into the session."""
        self._user = user
        self._remember_in_session(user)
        return user

    def login_using_id(self, user_id: Any) -> Optional[Any]:
        user = self.user_model().find(user_id)
        return self.login(user) if user is not None else None

    def set_user(self, user: Any) -> Any:
        """Set the user for this request only, without touching the session.

        Used when rehydrating from an existing session - writing back would
        rotate the session id on every request.
        """
        self._user = user
        return user

    def reset(self) -> None:
        """Clear in-request state without logging the user out of the session.

        The manager is a singleton, so a user resolved on one request must not
        leak into the next; but clearing memory is not the same as ending the
        session, which is what `logout()` does.
        """
        self._user = None

    def logout(self) -> None:
        """End the session - clears memory and forgets the stored user."""
        from engine.events.lifecycle import UserLoggedOut, fire

        # Captured before the reset, so listeners still see who left.
        departing = self._user
        self._user = None
        self._forget_session()
        if departing is not None:
            fire(UserLoggedOut(departing))

    # -- session persistence ---------------------------------------------------

    def set_session(self, session: Any) -> None:
        """Bind the current request's session so logins survive redirects."""
        self._session = session

    def _current_session(self) -> Any:
        return self._session

    def _session_key(self) -> str:
        from engine.http.middleware import Authenticate

        return Authenticate.SESSION_KEY

    def _remember_in_session(self, user: Any) -> None:
        session = self._current_session()
        if session is None or user is None:
            return
        # Rotate the id on login - otherwise a session fixed before login stays
        # valid afterwards (session fixation).
        session.regenerate()
        session.put(self._session_key(), user.get_attribute(self.primary_key_name()))
        # Step-up auth's freshness clock - every login (including a step-up
        # re-authentication that calls this indirectly) resets it.
        from engine.auth.step_up import StepUpAuth

        StepUpAuth.confirm(session)

    def _forget_session(self) -> None:
        session = self._current_session()
        if session is not None:
            # `invalidate()`, not just `forget()`: a stale-but-still-valid
            # session id left behind after logout is a lesser fixation risk
            # (nothing sensitive is keyed to it), but there is no reason to
            # keep it alive once the user has signed out.
            session.invalidate()

    def primary_key_name(self) -> str:
        return getattr(self.user_model(), "primary_key", "id")

    # -- authentication --------------------------------------------------------

    def validate(self, credentials: Dict[str, Any]) -> Optional[Any]:
        """Verify credentials without logging the user in."""
        credentials = dict(credentials or {})
        password = credentials.pop("password", None)
        if not credentials or password is None:
            return None

        query = self.user_model().query()
        for column, value in credentials.items():
            query = query.where(column, value)
        user = query.first()

        if user is None:
            # Compare against a dummy hash so a missing user costs the same as a
            # wrong password - otherwise timing reveals which emails exist.
            Hash.check(str(password), Hash.make("timing-equalizer"))
            return None

        if not Hash.check(str(password), user.get_attribute("password")):
            return None
        return user

    def attempt(
        self,
        credentials: Dict[str, Any],
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Validate credentials and log the user in on success."""
        from engine.events.lifecycle import UserAuthenticated, UserLoginFailed, fire

        identifier = str((credentials or {}).get("email") or (credentials or {}).get("username") or "")

        # Check honeypot & cooldown if service is available
        honeypot = None
        if self.app is not None:
            try:
                honeypot = self.app.make("honeypot")
            except Exception:
                pass

        client_ip = ip or "127.0.0.1"
        if honeypot is not None:
            is_blocked, _, _ = honeypot.check_cooldown(client_ip, identifier)
            if is_blocked:
                fire(UserLoginFailed(identifier))
                return False

        user = self.validate(credentials)
        if user is None:
            if honeypot is not None:
                honeypot.record_attempt(
                    ip=client_ip,
                    username=identifier,
                    user_agent=user_agent,
                    success=False,
                )
            fire(UserLoginFailed(identifier))
            return False

        if honeypot is not None:
            honeypot.record_attempt(
                ip=client_ip,
                username=identifier,
                user_agent=user_agent,
                success=True,
            )

        self.login(user)
        fire(UserAuthenticated(user))
        return True


    def once(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate for this request only, without touching the session.

        It used to be `validate(...) is not None` - it checked the credentials
        and authenticated nobody, so after a `True` return `Auth.check()` was
        still False and `Auth.user()` still None. That is `validate()` under a
        name that promises a login. The user is now set in memory; `login()`
        remains the one that also persists to the session.
        """
        user = self.validate(credentials)
        if user is None:
            return False
        self.set_user(user)
        return True

    # -- authorization helpers -------------------------------------------------

    def has_permission(self, slug: str) -> bool:
        if self._user is None:
            return False
        return bool(self._user.has_permission(slug))

    def is_admin(self) -> bool:
        if self._user is None:
            return False
        return bool(self._user.get_attribute("is_admin"))


__all__ = ["AuthManager", "Hash"]

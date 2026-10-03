"""Session handling for Craft Framework.

Two drivers ship by default:

* ``cookie`` — the whole payload lives in a signed cookie. No storage to set up,
  but the data is visible to the client and capped by cookie size.
* ``file``   — the cookie holds only an id; the payload lives under
  ``storage/framework/sessions``. Supports server-side invalidation.

Both sign the cookie with the application key, so a tampered cookie is rejected
rather than trusted.

Category: Core Framework (HTTP).
Relations:
  - Started by `StartSession` middleware (`engine/http/middleware.py`);
    read via `request.session()`; CSRF verification in the same middleware
    module consumes the session's token.
References:
  - Guide: `documentation/sessions.md`, `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

#: The session for the request being handled, set by the StartSession
#: middleware. Lets view helpers such as `csrf_field()` reach it without every
#: caller threading the request through.
current_session: ContextVar[Optional["Session"]] = ContextVar("current_session", default=None)


def get_current_session() -> Optional["Session"]:
    return current_session.get()

#: Keys used internally to carry flash data across exactly one request.
_FLASH_NEW = "__flash_new"
_FLASH_OLD = "__flash_old"
_TOKEN = "__csrf_token"


class Session:
    """Per-request session bag."""

    def __init__(self, data: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None):
        self._data: Dict[str, Any] = dict(data or {})
        self.id = session_id or secrets.token_urlsafe(24)
        #: The id this session was loaded with — lets the store destroy the old
        #: file when regenerate()/invalidate() hands out a new id.
        self._original_id = self.id
        self._modified = False

        # Data flashed on the previous request is readable now and then dropped.
        self._data[_FLASH_OLD] = self._data.pop(_FLASH_NEW, [])

    # -- basic access ----------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def put(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._modified = True

    def set(self, key: str, value: Any) -> None:
        self.put(key, value)

    def has(self, key: str) -> bool:
        return self._data.get(key) is not None

    def exists(self, key: str) -> bool:
        return key in self._data

    def forget(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._modified = True

    def pull(self, key: str, default: Any = None) -> Any:
        value = self.get(key, default)
        self.forget(key)
        return value

    def all(self) -> Dict[str, Any]:
        return {k: v for k, v in self._data.items() if not k.startswith("__")}

    def flush(self) -> None:
        """Drop every value but keep the session (and its CSRF token) alive."""
        token = self._data.get(_TOKEN)
        self._data = {}
        if token:
            self._data[_TOKEN] = token
        self._modified = True

    def invalidate(self) -> None:
        """Drop everything and take a new id — use after login/logout."""
        self._data = {}
        self.id = secrets.token_urlsafe(24)
        self.regenerate_token()
        self._modified = True

    def regenerate(self) -> None:
        """New id, same data — mitigates session fixation."""
        self.id = secrets.token_urlsafe(24)
        self._modified = True

    # -- flash data ------------------------------------------------------------

    def flash(self, key: str, value: Any) -> None:
        """Store a value readable on the next request only."""
        self._data[key] = value
        queued: List[str] = list(self._data.get(_FLASH_NEW, []))
        if key not in queued:
            queued.append(key)
        self._data[_FLASH_NEW] = queued
        self._modified = True

    def reflash(self) -> None:
        """Keep the current request's flash data for one more request."""
        old = list(self._data.get(_FLASH_OLD, []))
        self._data[_FLASH_NEW] = list(set(self._data.get(_FLASH_NEW, [])) | set(old))
        self._modified = True

    def age_flash_data(self) -> None:
        """Expire the previous request's flash keys. Called on save."""
        for key in self._data.get(_FLASH_OLD, []):
            if key not in self._data.get(_FLASH_NEW, []):
                self._data.pop(key, None)
        self._data.pop(_FLASH_OLD, None)

    # -- CSRF ------------------------------------------------------------------

    def token(self) -> str:
        """The CSRF token, created on first use."""
        if not self._data.get(_TOKEN):
            self.regenerate_token()
        return self._data[_TOKEN]

    def regenerate_token(self) -> str:
        self._data[_TOKEN] = secrets.token_urlsafe(32)
        self._modified = True
        return self._data[_TOKEN]

    # -- serialization ---------------------------------------------------------

    @property
    def modified(self) -> bool:
        return self._modified

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.put(key, value)

    def __repr__(self) -> str:
        return f"<Session {self.id[:8]}… {list(self.all())}>"


# -- signing --------------------------------------------------------------------

def sign(payload: str, key: str) -> str:
    digest = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify(payload: str, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign(payload, key), signature)


class SessionStore:
    """Base store: turns a Session into a cookie value and back."""

    def __init__(self, key: str, lifetime: int = 7200):
        self.key = key
        self.lifetime = lifetime

    def load(self, cookie_value: Optional[str]) -> Session:  # pragma: no cover
        raise NotImplementedError

    def save(self, session: Session) -> str:  # pragma: no cover
        raise NotImplementedError

    # -- shared helpers --------------------------------------------------------

    def _encode(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":"), default=str)
        encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")
        return f"{encoded}.{sign(encoded, self.key)}"

    def _decode(self, value: str) -> Optional[Dict[str, Any]]:
        if not value or "." not in value:
            return None
        encoded, _, signature = value.rpartition(".")
        if not verify(encoded, signature, self.key):
            return None  # tampered or signed with a different app key
        try:
            padding = "=" * (-len(encoded) % 4)
            raw = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        expires_at = data.pop("__expires_at", None)
        if expires_at is not None and float(expires_at) < time.time():
            return None
        return data


class CookieSessionStore(SessionStore):
    """Stores the whole payload in the signed cookie."""

    def load(self, cookie_value: Optional[str]) -> Session:
        data = self._decode(cookie_value) if cookie_value else None
        return Session(data or {})

    def save(self, session: Session) -> str:
        session.age_flash_data()
        data = session.to_dict()
        data["__expires_at"] = time.time() + self.lifetime
        return self._encode(data)


class FileSessionStore(SessionStore):
    """Stores the payload on disk; the cookie carries only a signed id."""

    def __init__(self, key: str, directory: str, lifetime: int = 7200):
        super().__init__(key, lifetime)
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, session_id: str) -> str:
        # Hash the id so a crafted id can never escape the directory.
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return os.path.join(self.directory, f"{digest}.session")

    def load(self, cookie_value: Optional[str]) -> Session:
        payload = self._decode(cookie_value) if cookie_value else None
        session_id = (payload or {}).get("id")
        if not session_id:
            return Session({})

        path = self._path(session_id)
        if not os.path.isfile(path):
            return Session({}, session_id=session_id)

        try:
            with open(path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, ValueError):
            return Session({}, session_id=session_id)

        if stored.get("__expires_at", 0) < time.time():
            self.destroy(session_id)
            return Session({}, session_id=session_id)

        stored.pop("__expires_at", None)
        return Session(stored, session_id=session_id)

    def save(self, session: Session) -> str:
        session.age_flash_data()
        data = session.to_dict()
        data["__expires_at"] = time.time() + self.lifetime

        # regenerate()/invalidate() changed the id — destroy the old file so a
        # fixated cookie cannot keep resurrecting the pre-rotation session.
        original_id = getattr(session, "_original_id", None)
        if original_id and original_id != session.id:
            self.destroy(original_id)
            session._original_id = session.id

        try:
            with open(self._path(session.id), "w", encoding="utf-8") as handle:
                json.dump(data, handle, default=str)
        except OSError:
            pass
        return self._encode({"id": session.id})

    def destroy(self, session_id: str) -> None:
        try:
            os.remove(self._path(session_id))
        except OSError:
            pass

    def gc(self) -> int:
        """Delete expired session files. Returns how many were removed."""
        removed = 0
        if not os.path.isdir(self.directory):
            return 0
        for name in os.listdir(self.directory):
            if not name.endswith(".session"):
                continue
            path = os.path.join(self.directory, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    stored = json.load(handle)
                if stored.get("__expires_at", 0) < time.time():
                    os.remove(path)
                    removed += 1
            except (OSError, ValueError):
                continue
        return removed


class DatabaseSessionStore(SessionStore):
    """Server-side session storage in the `sessions` table.

    Unlike `CookieSessionStore` and `FileSessionStore`, a row here can be
    revoked from outside the browser that holds it — "log out everywhere,"
    an admin ending a compromised session, a password change invalidating
    every other session — and idle time is tracked independent of the
    cookie's own absolute expiry, so a session left open in an unattended
    browser can be timed out sooner than its full lifetime.
    """

    #: An unmodified session refreshes `last_activity_at` at most this often,
    #: so reads keep a user active without one write per request.
    ACTIVITY_TOUCH_SECONDS = 60

    def __init__(self, key: str, app: Any = None, lifetime: int = 7200, idle_timeout: Optional[int] = None):
        super().__init__(key, lifetime)
        self.app = app
        #: Seconds of inactivity before a session is treated as expired,
        #: independent of `lifetime`. `None` disables idle checking.
        self.idle_timeout = idle_timeout

    def _db(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("db")
            except Exception:
                pass
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def load(self, cookie_value: Optional[str]) -> Session:
        payload = self._decode(cookie_value) if cookie_value else None
        session_id = (payload or {}).get("id")
        if not session_id:
            return Session({})

        db = self._db()
        try:
            row = db.table("sessions").where("id", session_id).first()
        except Exception:
            return Session({}, session_id=session_id)
        if row is None:
            return Session({}, session_id=session_id)

        if row.get("revoked_at"):
            # Revoked from outside this request — a still-signed cookie must
            # not resurrect it. Same treatment as an expired one: a fresh
            # session under the same id, not an error.
            return Session({}, session_id=session_id)

        if self._is_idle_expired(row) or self._is_lifetime_expired(row):
            self.destroy(session_id)
            return Session({}, session_id=session_id)

        try:
            stored = json.loads(row.get("payload") or "{}")
        except ValueError:
            stored = {}
        session = Session(stored, session_id=session_id)
        session._modified = False
        session._persisted = True
        session._last_activity = self._parse_stored_time(row.get("last_activity_at"))
        return session

    def _is_lifetime_expired(self, row: Dict[str, Any]) -> bool:
        created_at = self._parse_stored_time(row.get("created_at"))
        return created_at is not None and (time.time() - created_at) > self.lifetime

    def _is_idle_expired(self, row: Dict[str, Any]) -> bool:
        if self.idle_timeout is None:
            return False
        last_activity = self._parse_stored_time(row.get("last_activity_at"))
        return last_activity is not None and (time.time() - last_activity) > self.idle_timeout

    def _touch_activity(self, session: Session) -> None:
        """Record activity on an unmodified session, at most once per interval.

        Args:
            session: A persisted session whose payload did not change.
        """
        last = getattr(session, "_last_activity", None)
        if last is not None and time.time() - last < self.ACTIVITY_TOUCH_SECONDS:
            return
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            self._db().table("sessions").where("id", session.id).update(
                {"last_activity_at": now, "updated_at": now}
            )
        except Exception:
            return
        session._last_activity = time.time()

    @staticmethod
    def _parse_stored_time(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                import datetime as _dt

                return _dt.datetime.strptime(str(value)[:26], fmt).replace(tzinfo=_dt.timezone.utc).timestamp()
            except ValueError:
                continue
        return None

    def save(self, session: Session) -> str:
        session.age_flash_data()
        original_id = getattr(session, "_original_id", None)
        id_changed = bool(original_id and original_id != session.id)

        # A read-only request does not rewrite the payload, but it is still
        # activity: idle tracking would log out a user who only reads.
        if not session._modified and not id_changed and getattr(session, "_persisted", False):
            self._touch_activity(session)
            return self._encode({"id": session.id})

        payload = json.dumps(session.to_dict(), default=str)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db = self._db()

        if id_changed:
            self.destroy(original_id)
            session._original_id = session.id

        try:
            if getattr(session, "_persisted", False) and not id_changed:
                db.table("sessions").where("id", session.id).update({
                    "payload": payload, "last_activity_at": now, "updated_at": now,
                })
            else:
                existing = db.table("sessions").where("id", session.id).first()
                if existing:
                    db.table("sessions").where("id", session.id).update({
                        "payload": payload, "last_activity_at": now, "updated_at": now,
                    })
                else:
                    db.table("sessions").insert({
                        "id": session.id, "payload": payload,
                        "last_activity_at": now, "created_at": now, "updated_at": now,
                    })
                session._persisted = True
        except Exception:
            pass
        session._modified = False
        session._last_activity = time.time()
        return self._encode({"id": session.id})

    def destroy(self, session_id: str) -> None:
        try:
            self._db().table("sessions").where("id", session_id).delete()
        except Exception:
            pass

    def revoke(self, session_id: str) -> None:
        """Mark a session unusable immediately, without deleting its row.

        Kept (not deleted) rather than destroyed outright, so an audit trail
        of "this session was forcibly ended, and when" survives the act that
        ended it — `destroy()` is for an expired or logged-out session with
        nothing worth keeping; `revoke()` is for one ended *on purpose*.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            self._db().table("sessions").where("id", session_id).update({"revoked_at": now})
        except Exception:
            pass

    def revoke_all_for(self, except_session_id: Optional[str] = None) -> int:
        """Revoke every session except one — "log out everywhere but here."

        Args:
            except_session_id: A session id to leave untouched (typically the
                caller's own current session).

        Returns:
            How many sessions were revoked.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db = self._db()
        try:
            query = db.table("sessions").where_null("revoked_at")
            if except_session_id:
                query = query.where("id", "!=", except_session_id)
            rows = query.get()
            for row in rows:
                db.table("sessions").where("id", row["id"]).update({"revoked_at": now})
            return len(rows)
        except Exception:
            return 0

    def gc(self) -> int:
        """Delete rows past their absolute lifetime. Returns how many were removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.lifetime)).strftime("%Y-%m-%d %H:%M:%S")
        db = self._db()
        try:
            return db.table("sessions").where("created_at", "<", cutoff).delete()
        except Exception:
            return 0


#: One fallback signing key per process, created on first use. It must be
#: stable — a fresh key per store instance would silently invalidate every
#: cookie the moment anything rebuilt the store.
_EPHEMERAL_KEY: Optional[str] = None


def _ephemeral_key() -> str:
    global _EPHEMERAL_KEY
    if _EPHEMERAL_KEY is None:
        _EPHEMERAL_KEY = secrets.token_urlsafe(32)
    return _EPHEMERAL_KEY


def make_store(app: Any = None) -> SessionStore:
    """Build the configured session store."""
    config = None
    if app is not None:
        try:
            config = app.make("config")
        except Exception:
            config = None

    def setting(key: str, default: Any) -> Any:
        return config.get(key, default) if config else default

    app_key = str(setting("app.APP_KEY", "") or setting("app.app_key", "") or "")
    if not app_key:
        env = str(setting("app.APP_ENV", "") or setting("app.env", "") or "").lower()
        if env == "production":
            # Fail loud, mirroring the unknown-middleware-alias pattern in
            # `engine/http/kernel.py` — an ephemeral per-process key in
            # production silently breaks sessions across restarts/workers,
            # and would make the failure mode "sessions randomly stop
            # working" instead of an obvious boot-time error.
            raise RuntimeError(
                "APP_KEY is empty in a production environment (APP_ENV=production). "
                "Run `python dev.py key:generate` to write a real APP_KEY before "
                "starting the app — an ephemeral per-process key would silently "
                "invalidate every session on restart or across workers."
            )
        # Never sign with an empty key — that would make forgery trivial. Fall
        # back to one random key per process: sessions work, but they do not
        # survive a restart and are not shared between workers, until
        # `dev key:generate` writes a real APP_KEY. Non-production only.
        app_key = _ephemeral_key()

    lifetime = int(setting("session.lifetime", 7200) or 7200)
    driver = str(setting("session.driver", "cookie") or "cookie").lower()

    if driver == "file":
        base_path = getattr(app, "base_path", os.getcwd())
        directory = setting(
            "session.files", os.path.join(base_path, "storage", "framework", "sessions")
        )
        return FileSessionStore(app_key, directory, lifetime)

    if driver == "database":
        idle_timeout = setting("session.idle_timeout", None)
        return DatabaseSessionStore(
            app_key, app, lifetime, int(idle_timeout) if idle_timeout else None
        )

    return CookieSessionStore(app_key, lifetime)


__all__ = [
    "Session",
    "SessionStore",
    "CookieSessionStore",
    "FileSessionStore",
    "DatabaseSessionStore",
    "make_store",
    "sign",
    "verify",
    "current_session",
    "get_current_session",
]

"""
Honeypot, Authentication Audit & Brute-force Cooldown Subsystem.
Category: Core Framework (Security).
Relations:
  - Consumed by `engine/auth/manager.py` and security middlewares.
  - Interacts with `auth_audit_logs`, `auth_cooldowns` and `security_events` tables via `DB`.
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


class HoneypotService:
    """Detects and neutralizes malicious login attempts, maintaining audit trails and cooldowns."""

    #: Commonly targeted administrative accounts trapped on login attempts.
    ABUSED_USERNAMES: Set[str] = {
        "admin", "administrator", "root", "system", "test", "guest",
        "user", "manager", "support", "webmaster", "superuser",
        "operator", "postgres", "dbadmin", "master", "default"
    }

    MAX_FAILED_ATTEMPTS: int = 5
    COOLDOWN_MINUTES: int = 30
    #: Failures older than this many minutes no longer count toward the
    #: current streak — a sliding window, not a lifetime counter, so an
    #: account that failed once last week and once today is not treated the
    #: same as five failures in the last minute.
    WINDOW_MINUTES: int = 15

    def __init__(self, app: Any = None):
        self.app = app

    def _db(self) -> Any:
        if self.app is not None:
            try:
                return self.app.make("db")
            except Exception:
                pass
        from engine.container.application import Container
        return Container.getInstance().make("db")

    def is_honeypot_target(self, username: str) -> bool:
        """Check whether the given username matches a known honeypot trap target."""
        if not username or not isinstance(username, str):
            return False
        clean = username.strip().lower()
        return clean in self.ABUSED_USERNAMES

    def _format_time(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _hash_username(username: str) -> str:
        """A username often is an email address - PII with no business being
        stored in clear in a table whose only job is counting attempts. A
        plain SHA-256 (not keyed) is enough here: the goal is not secrecy
        against a determined attacker, it is not leaking the value at rest
        in a table an operator, a backup, or a support ticket might expose,
        while `check_cooldown()` still needs an exact-match lookup, which a
        deterministic hash gives for free.
        """
        return hashlib.sha256(username.encode("utf-8")).hexdigest()

    # -- audit chain -----------------------------------------------------------

    #: `previous_hash` of the first row in the chain.
    GENESIS_HASH: str = "0" * 64

    @staticmethod
    def _entry_hash(
        previous: str,
        *,
        ip: str,
        username: str,
        user_agent: str,
        result: str,
        reason: str,
        created_at: str,
    ) -> str:
        """Digest of one audit row together with the row before it.

        Fields are joined with a NUL byte, which none of them can contain, so
        two different rows cannot collide by shifting a separator into a value.
        Any single change to a field — or to `previous_hash` — changes the
        digest, and the next row's `previous_hash` no longer matches.
        """
        payload = "\x00".join([previous, ip, username, user_agent, result, reason, created_at])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _last_chain_hash(self, db: Any) -> str:
        """Return the newest audit row's `chain_hash`, or the genesis value."""
        try:
            row = db.table("auth_audit_logs").order_by("id", "desc").limit(1).first()
        except Exception:
            row = None
        if row and row.get("chain_hash"):
            return row["chain_hash"]
        return self.GENESIS_HASH

    def _append_audit_log(
        self,
        db: Any,
        *,
        ip: str,
        username: str,
        user_agent: str,
        result: str,
        reason: str,
        created_at: str,
    ) -> None:
        """Insert one audit row, linked to the previous row's hash.

        The chain assumes a single writer: two truly concurrent inserts could
        read the same `previous_hash` and fork it, which a chain check reports
        rather than hides. A database that has not run the chain migration yet
        still gets its audit row, unchained — the chain starts once the columns
        exist.
        """
        entry = {
            "ip_address": ip,
            "username": username,
            "user_agent": user_agent,
            "result": result,
            "reason": reason,
            "created_at": created_at,
        }
        try:
            previous = self._last_chain_hash(db)
            db.table("auth_audit_logs").insert({
                **entry,
                "previous_hash": previous,
                "chain_hash": self._entry_hash(
                    previous, ip=ip, username=username, user_agent=user_agent,
                    result=result, reason=reason, created_at=created_at,
                ),
            })
        except Exception:
            db.table("auth_audit_logs").insert(entry)

    def _parse_time(self, val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
        if isinstance(val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
                try:
                    parsed = datetime.strptime(val.rstrip("Z"), fmt)
                    return parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
        return None

    def check_cooldown(self, ip: str, username: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """Verify if an IP address or username is currently blocked under a cooldown period.
        
        Returns: (is_blocked, blocked_until, reason)
        """
        now = datetime.now(timezone.utc)
        clean_user = (username or "").strip().lower()
        user_hash = self._hash_username(clean_user) if clean_user else None

        db = self._db()
        try:
            lookup = [ip] + ([user_hash] if user_hash else [])
            records = db.table("auth_cooldowns") \
                .where_in("identifier_value", lookup) \
                .get()
        except Exception:
            return False, None, None

        for rec in records:
            blocked_until = self._parse_time(rec.get("blocked_until"))
            if blocked_until and blocked_until > now:
                reason = f"Too many failed login attempts for {rec.get('identifier_type')}. Cooldown active."
                return True, blocked_until, reason

        return False, None, None

    def record_attempt(
        self,
        ip: str,
        username: str,
        user_agent: Optional[str] = None,
        success: bool = False,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record login attempt, update cooldowns, and trigger honeypot alerts if applicable."""
        now = datetime.now(timezone.utc)
        now_str = self._format_time(now)
        clean_user = (username or "empty").strip().lower()
        ua_string = (user_agent or "")[:500]
        db = self._db()

        # 1. Honeypot Trap Trigger
        if self.is_honeypot_target(clean_user):
            try:
                self._append_audit_log(
                    db,
                    ip=ip,
                    username=clean_user,
                    user_agent=ua_string,
                    result="HONEYPOT",
                    reason="ABUSED_USERNAME_TRAP",
                    created_at=now_str,
                )
                db.table("security_events").insert({
                    "ip_address": ip,
                    "event_type": "HONEYPOT_HIT",
                    "request_uri": "/login",
                    "request_method": "POST",
                    "payload_sample": f"Trapped username: {clean_user}",
                    "score_increment": 40,
                    "created_at": now_str,
                })
                # Enforce immediate 30-minute block on the attacking IP - a
                # direct override (not an increment), so a plain upsert is
                # enough; nothing here depends on an existing count.
                blocked_until = self._format_time(now + timedelta(minutes=self.COOLDOWN_MINUTES))
                db.statement(
                    "INSERT INTO auth_cooldowns "
                    "(identifier_type, identifier_value, failed_attempts, blocked_until, created_at, updated_at) "
                    "VALUES ('ip', ?, ?, ?, ?, ?) "
                    "ON CONFLICT (identifier_type, identifier_value) "
                    "DO UPDATE SET failed_attempts = ?, blocked_until = excluded.blocked_until, "
                    "updated_at = excluded.updated_at",
                    [ip, self.MAX_FAILED_ATTEMPTS, blocked_until, now_str, now_str, self.MAX_FAILED_ATTEMPTS],
                )
            except Exception:
                pass
            return {"status": "HONEYPOT", "blocked": True, "reason": "ABUSED_USERNAME_TRAP"}

        # 2. Regular Authentication Audit Log
        result_status = "SUCCESS" if success else "FAILED"
        final_reason = reason or ("AUTHENTICATED" if success else "INVALID_CREDENTIALS")

        try:
            self._append_audit_log(
                db,
                ip=ip,
                username=clean_user,
                user_agent=ua_string,
                result=result_status,
                reason=final_reason,
                created_at=now_str,
            )
        except Exception:
            pass

        user_hash = self._hash_username(clean_user) if clean_user and clean_user != "empty" else None

        if success:
            # Clear previous failed attempts.
            try:
                db.table("auth_cooldowns").where("identifier_value", ip).delete()
                if user_hash:
                    db.table("auth_cooldowns").where("identifier_value", user_hash).delete()
            except Exception:
                pass
            return {"status": "SUCCESS", "blocked": False, "reason": final_reason}

        # 3. Failed Attempt Cooldown Tracking — atomic increment (see
        # _atomic_increment_cooldown's docstring for why this cannot be a
        # separate read-then-write).
        blocked = False
        candidates = [(ip, "ip")] + ([(user_hash, "username")] if user_hash else [])
        for id_val, id_type in candidates:
            try:
                attempts = self._atomic_increment_cooldown(id_val, id_type, now_str)
                if attempts >= self.MAX_FAILED_ATTEMPTS:
                    blocked = True
                    blocked_until = self._format_time(now + timedelta(minutes=self.COOLDOWN_MINUTES))
                    db.table("auth_cooldowns") \
                        .where("identifier_type", id_type) \
                        .where("identifier_value", id_val) \
                        .update({"blocked_until": blocked_until, "updated_at": now_str})
            except Exception:
                pass

        return {"status": "FAILED", "blocked": blocked, "reason": final_reason}

    def _atomic_increment_cooldown(self, identifier_value: str, identifier_type: str, now_str: str) -> int:
        """Atomically increment `failed_attempts`, returning the new count.

        The previous implementation read the current count, added one in
        Python, and wrote it back in a separate statement — two concurrent
        failed logins for the same IP or username (exactly what an automated
        brute-force tool produces) could both read the same count and both
        write `count + 1`, silently losing an increment. `INSERT ... ON
        CONFLICT ... DO UPDATE SET failed_attempts = failed_attempts + 1` is
        a single, database-level atomic operation instead: the increment
        happens inside the database's own row lock, so no interleaving of two
        concurrent calls can lose one.

        Only `blocked_until` is set separately, once the caller knows whether
        this count crossed the threshold — that second write does not need to
        be atomic with the first, because every racing caller that crosses
        the threshold computes the same `blocked_until` value from the same
        clock read, so a "lost" second write just means a harmless duplicate.

        A sliding window, not a lifetime counter: the `CASE` resets the count
        to 1 instead of incrementing when the row's last update falls outside
        `WINDOW_MINUTES`, so a failure from last week does not sit in the same
        streak as one from a minute ago — still one atomic statement, the
        window check included.
        """
        db = self._db()
        window_start = self._format_time(
            datetime.now(timezone.utc) - timedelta(minutes=self.WINDOW_MINUTES)
        )
        result = db.statement(
            "INSERT INTO auth_cooldowns "
            "(identifier_type, identifier_value, failed_attempts, blocked_until, created_at, updated_at) "
            "VALUES (?, ?, 1, ?, ?, ?) "
            "ON CONFLICT (identifier_type, identifier_value) "
            "DO UPDATE SET failed_attempts = CASE "
            "    WHEN auth_cooldowns.updated_at < ? THEN 1 "
            "    ELSE auth_cooldowns.failed_attempts + 1 "
            "  END, "
            "  updated_at = excluded.updated_at "
            "RETURNING failed_attempts",
            [identifier_type, identifier_value, now_str, now_str, now_str, window_start],
        )
        row = result.fetchone()
        return int(row["failed_attempts"]) if row is not None else 1


__all__ = ["HoneypotService"]

"""
Web Application Firewall (WAF) & Intrusion Detection System (IDS) for Craft Framework.
Features: IP Whitelist/Blacklist, Anomaly Scoring, SQLi/XSS/SSRF/Traversal Detection.
Category: Core Framework (Security).
Relations:
  - Consumed as `Firewall` facade and `FirewallMiddleware` in `engine/http/middleware.py`.
  - Persists threat logs and reputation to `firewall_rules` and `security_events` tables via `DB`.
References:
  - Guide: `documentation/security.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from starlette.responses import JSONResponse


class Firewall:
    """Core WAF & Threat Intelligence engine."""

    BLACKLIST_THRESHOLD_SCORE: int = 100

    # Threat Signatures (Regular Expressions)
    SQLI_PATTERNS = re.compile(
        r"(\b(UNION(\s+ALL)?|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE)\b|"
        r"['\"]\s*OR\s*['\"]?1['\"]?\s*=\s*['\"]?1|--|\/\*|\*\/|;\s*SHUTDOWN)",
        re.IGNORECASE,
    )
    XSS_PATTERNS = re.compile(
        r"(<script.*?>|javascript:|onload\s*=|onerror\s*=|document\.cookie|<iframe.*?>)",
        re.IGNORECASE,
    )
    TRAVERSAL_PATTERNS = re.compile(
        r"(\.\./|\.\.\\|/etc/passwd|/proc/self|/windows/win\.ini)",
        re.IGNORECASE,
    )
    SSRF_TARGETS = re.compile(
        r"(169\.254\.169\.254|localhost|127\.0\.0\.1|0\.0\.0\.0|internal\.corp)",
        re.IGNORECASE,
    )

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

    def _format_time(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _config(self, key: str, default: Any) -> Any:
        if self.app is not None:
            try:
                return self.app.make("config").get(key, default)
            except Exception:
                pass
        try:
            from engine.container.application import Container

            return Container.getInstance().make("config").get(key, default)
        except Exception:
            return default

    def _cidr_rules(self, status: str) -> List[str]:
        """`firewall_rules` rows whose `ip_address` is a CIDR range (contains `/`).

        A single-IP rule is found by an exact `WHERE ip_address = ?`, cheap
        and index-friendly; a CIDR rule cannot be, so it needs its own,
        separately-fetched set checked in Python via `ipaddress`.
        """
        db = self._db()
        try:
            rows = db.table("firewall_rules").where("status", status).get()
        except Exception:
            return []
        return [row["ip_address"] for row in rows if "/" in str(row.get("ip_address") or "")]

    def _matches_any_cidr(self, ip: str, status: str) -> bool:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return False
        for cidr in self._cidr_rules(status):
            try:
                if address in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def whitelist_ip(self, ip: str) -> None:
        """Add an IP to the trusted whitelist (bypasses rate limits and inspection)."""
        now = self._format_time(datetime.now(timezone.utc))
        db = self._db()
        existing = db.table("firewall_rules").where("ip_address", ip).first()
        if existing:
            db.table("firewall_rules").where("ip_address", ip).update({
                "status": "whitelist",
                "reputation_score": 0,
                "blocked_reason": None,
                "updated_at": now,
            })
        else:
            db.table("firewall_rules").insert({
                "ip_address": ip,
                "reputation_score": 0,
                "status": "whitelist",
                "blocked_reason": None,
                "created_at": now,
                "updated_at": now,
            })

    def blacklist_ip(self, ip: str, reason: str = "Manual administrator block") -> None:
        """Add an IP to the permanent blacklist (blocked immediately on all endpoints)."""
        now = self._format_time(datetime.now(timezone.utc))
        db = self._db()
        existing = db.table("firewall_rules").where("ip_address", ip).first()
        if existing:
            db.table("firewall_rules").where("ip_address", ip).update({
                "status": "blacklist",
                "reputation_score": max(int(existing.get("reputation_score") or 0), self.BLACKLIST_THRESHOLD_SCORE),
                "blocked_reason": reason,
                "updated_at": now,
            })
        else:
            db.table("firewall_rules").insert({
                "ip_address": ip,
                "reputation_score": self.BLACKLIST_THRESHOLD_SCORE,
                "status": "blacklist",
                "blocked_reason": reason,
                "created_at": now,
                "updated_at": now,
            })

    def is_whitelisted(self, ip: str) -> bool:
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).where("status", "whitelist").first()
            if row is not None:
                return True
        except Exception:
            return False
        return self._matches_any_cidr(ip, "whitelist")

    def is_blacklisted(self, ip: str) -> bool:
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).where("status", "blacklist").first()
            if row is not None:
                return True
        except Exception:
            return False
        return self._matches_any_cidr(ip, "blacklist")

    def get_reputation_score(self, ip: str) -> int:
        """Current score, decayed for time elapsed since the last event.

        `FIREWALL_REPUTATION_DECAY_PER_DAY` points are subtracted per full day
        since `last_event_at`, floored at 0 — an IP that has been clean for a
        long time should not still be judged by one old incident.
        """
        db = self._db()
        try:
            row = db.table("firewall_rules").where("ip_address", ip).first()
        except Exception:
            return 0
        if not row:
            return 0
        return self._decayed_score(row)

    def _decayed_score(self, row: Dict[str, Any]) -> int:
        score = int(row.get("reputation_score") or 0)
        decay_per_day = int(self._config("firewall.reputation_decay_per_day", 5) or 0)
        last_event_at = row.get("last_event_at")
        if decay_per_day <= 0 or not last_event_at:
            return score
        try:
            last_event = datetime.strptime(str(last_event_at)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return score
        days_elapsed = (datetime.now(timezone.utc) - last_event).days
        return max(0, score - days_elapsed * decay_per_day)

    def inspect_payload(self, text: str) -> Optional[Tuple[str, int]]:
        """Inspect text for malicious payload signatures. Returns (threat_type, score_increment)."""
        if not text or not isinstance(text, str):
            return None
        if self.SQLI_PATTERNS.search(text):
            return "SQL_INJECTION_DETECTED", 50
        if self.XSS_PATTERNS.search(text):
            return "XSS_INJECTION_DETECTED", 30
        if self.TRAVERSAL_PATTERNS.search(text):
            return "PATH_TRAVERSAL_DETECTED", 40
        if self.SSRF_TARGETS.search(text):
            return "SSRF_ATTEMPT_DETECTED", 50
        return None

    def record_threat(
        self,
        ip: str,
        threat_type: str,
        score_increment: int,
        uri: str = "",
        method: str = "GET",
        sample: str = "",
    ) -> bool:
        """Record threat event and update IP reputation score. Returns True if IP became blacklisted."""
        now = datetime.now(timezone.utc)
        now_str = self._format_time(now)
        db = self._db()

        try:
            db.table("security_events").insert({
                "ip_address": ip,
                "event_type": threat_type,
                "request_uri": (uri or "")[:500],
                "request_method": (method or "GET")[:10],
                "payload_sample": (sample or "")[:1000],
                "score_increment": score_increment,
                "created_at": now_str,
            })
        except Exception:
            pass

        try:
            existing = db.table("firewall_rules").where("ip_address", ip).first()
            current_score = (int(existing.get("reputation_score") or 0) + score_increment) if existing else score_increment
            new_status = "blacklist" if current_score >= self.BLACKLIST_THRESHOLD_SCORE else (
                existing.get("status", "monitored") if existing else "monitored"
            )

            if existing:
                db.table("firewall_rules").where("ip_address", ip).update({
                    "reputation_score": current_score,
                    "status": new_status,
                    "blocked_reason": threat_type if new_status == "blacklist" else existing.get("blocked_reason"),
                    "last_event_at": now_str,
                    "updated_at": now_str,
                })
            else:
                db.table("firewall_rules").insert({
                    "ip_address": ip,
                    "reputation_score": current_score,
                    "status": new_status,
                    "blocked_reason": threat_type if new_status == "blacklist" else None,
                    "last_event_at": now_str,
                    "created_at": now_str,
                    "updated_at": now_str,
                })

            return new_status == "blacklist"
        except Exception:
            return False


class FirewallMiddleware:
    """Synchronous middleware that inspects requests against WAF and reputation rules."""

    alias_parameters: tuple = ()

    def __init__(self, app: Any = None):
        self.app = app
        self._firewall = Firewall(app)

    def _extract_ip(self, request: Any) -> str:
        """Return the client address, never the client-chosen forwarded prefix."""
        from engine.security.net import client_ip

        return client_ip(request)

    def _is_health_exempt(self, request: Any) -> bool:
        """Whether this path skips the firewall entirely.

        An automated health check hitting the same path thousands of times a
        day should not trip threat detection or accumulate a reputation
        score it did nothing to earn.
        """
        path = str(getattr(getattr(request, "url", None), "path", ""))
        exempt = str(self._firewall._config("firewall.health_exempt_paths", "") or "")
        return path in {segment.strip() for segment in exempt.split(",") if segment.strip()}

    def _shadow_mode(self) -> bool:
        return bool(self._firewall._config("firewall.shadow_mode", False))

    def handle(self, request: Any, next_callable: Callable) -> Any:
        if self._is_health_exempt(request):
            return next_callable(request)

        ip = self._extract_ip(request)
        shadow = self._shadow_mode()

        # 1. Check IP Whitelist / Blacklist
        if self._firewall.is_whitelisted(ip):
            return next_callable(request)

        if self._firewall.is_blacklisted(ip) and not shadow:
            from engine.exceptions.handler import AuthorizationException
            if getattr(request, "expects_json", lambda: False)():
                return JSONResponse(
                    {"error": "Access denied by firewall security policy.", "code": "IP_BLACKLISTED"},
                    status_code=403,
                )
            raise AuthorizationException("Access denied by firewall security policy.")

        # 2. Inspect URI and Query String for threat signatures
        url_path = str(getattr(getattr(request, "url", None), "path", ""))
        query_string = str(getattr(getattr(request, "url", None), "query", ""))
        sample = f"{url_path} ? {query_string}"

        threat = self._firewall.inspect_payload(sample)
        if threat:
            threat_type, score_inc = threat
            method = getattr(request, "method", "GET")
            # Recorded even in shadow mode - the point is to see what the
            # rule *would* have scored before it can turn away real traffic.
            self._firewall.record_threat(
                ip=ip,
                threat_type=threat_type,
                score_increment=score_inc,
                uri=url_path,
                method=method,
                sample=sample,
            )

            if shadow:
                return next_callable(request)

            from engine.exceptions.handler import AuthorizationException
            if getattr(request, "expects_json", lambda: False)():
                return JSONResponse(
                    {"error": "Malicious payload signature detected.", "incident_ref": threat_type},
                    status_code=403,
                )
            raise AuthorizationException(f"Malicious payload signature detected: {threat_type}")

        return next_callable(request)


__all__ = ["Firewall", "FirewallMiddleware"]

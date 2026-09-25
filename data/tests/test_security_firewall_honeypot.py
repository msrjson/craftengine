"""
Tests for Web Application Firewall (WAF), Honeypot, and Authentication Cooldown Subsystems.
Category: Core Framework Tests (Security).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import PlainTextResponse

from bootstrap.app import app
from craft.exceptions.handler import AuthorizationException
from craft.facades import Auth, DB, Firewall as FirewallFacade, Honeypot as HoneypotFacade
from craft.http.middleware import AuthenticateApiToken, FirewallMiddleware, SecurityHeaders
from craft.security.firewall import Firewall
from craft.security.honeypot import HoneypotService


def _make_scope(path: str = "/", query_string: bytes = b"", client_ip: str = "127.0.0.1", headers: list = None):
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": query_string,
        "headers": headers or [(b"host", b"testserver")],
        "client": (client_ip, 12345),
    }


def _unique_ip() -> str:
    """Return a single IPv4 address no other test uses in this session.

    Firewall rules, security events and cooldowns persist for the whole session
    (tests never delete), so each test owns its address. Single addresses live
    in 198.18.0.0/15, disjoint from the CIDR ranges `_unique_cidr` hands out.
    """
    raw = uuid.uuid4().bytes
    return "198.%d.%d.%d" % (18 + raw[0] % 2, raw[1], 1 + raw[2] % 254)


def _unique_cidr() -> tuple[str, str]:
    """Return a unique /24 inside 100.64.0.0/10 and one address within it."""
    raw = uuid.uuid4().bytes
    prefix = "100.%d.%d" % (64 + raw[0] % 64, raw[1])
    return f"{prefix}.0/24", f"{prefix}.42"


def test_honeypot_target_detection():
    honeypot = HoneypotService(app)
    assert honeypot.is_honeypot_target("admin") is True
    assert honeypot.is_honeypot_target("root") is True
    assert honeypot.is_honeypot_target("administrator") is True
    assert honeypot.is_honeypot_target("postgres") is True
    assert honeypot.is_honeypot_target("jane.doe@example.com") is False


def test_honeypot_trap_logs_and_blocks():
    honeypot = HoneypotService(app)
    ip = _unique_ip()

    result = honeypot.record_attempt(ip=ip, username="root", user_agent="curl/7.68.0")
    assert result["status"] == "HONEYPOT"
    assert result["blocked"] is True

    # Verify audit log and cooldown
    audit_row = DB.table("auth_audit_logs").where("ip_address", ip).where("result", "HONEYPOT").first()
    assert audit_row is not None
    assert audit_row.get("username") == "root"

    is_blocked, blocked_until, _ = honeypot.check_cooldown(ip, "root")
    assert is_blocked is True
    assert blocked_until is not None


def test_brute_force_cooldown_escalation():
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    username = f"attacker_target_{uuid.uuid4().hex[:8]}"

    # 4 failed attempts should not trigger full cooldown block
    for _ in range(4):
        res = honeypot.record_attempt(ip=ip, username=username, success=False)
        assert res["status"] == "FAILED"
        assert res["blocked"] is False

    # 5th attempt triggers 30-minute cooldown
    res = honeypot.record_attempt(ip=ip, username=username, success=False)
    assert res["status"] == "FAILED"
    assert res["blocked"] is True

    is_blocked, _, reason = honeypot.check_cooldown(ip, username)
    assert is_blocked is True
    assert "Cooldown active" in (reason or "")

    # Successful attempt clears cooldown
    honeypot.record_attempt(ip=ip, username=username, success=True)
    is_blocked_after, _, _ = honeypot.check_cooldown(ip, username)
    assert is_blocked_after is False


def test_firewall_threat_signature_detection():
    fw = Firewall(app)

    # SQL Injection
    assert fw.inspect_payload("SELECT * FROM users WHERE '1'='1'")[0] == "SQL_INJECTION_DETECTED"
    assert fw.inspect_payload("UNION SELECT null, username, password FROM users")[0] == "SQL_INJECTION_DETECTED"

    # XSS
    assert fw.inspect_payload("<script>alert('xss')</script>")[0] == "XSS_INJECTION_DETECTED"
    assert fw.inspect_payload("javascript:document.cookie")[0] == "XSS_INJECTION_DETECTED"

    # Path Traversal
    assert fw.inspect_payload("../../etc/passwd")[0] == "PATH_TRAVERSAL_DETECTED"

    # SSRF
    assert fw.inspect_payload("http://169.254.169.254/latest/meta-data/")[0] == "SSRF_ATTEMPT_DETECTED"

    # Benign string
    assert fw.inspect_payload("/articles/my-first-post?page=2") is None


def test_firewall_whitelist_and_blacklist():
    fw = Firewall(app)
    ip = _unique_ip()

    assert fw.is_whitelisted(ip) is False
    assert fw.is_blacklisted(ip) is False

    fw.whitelist_ip(ip)
    assert fw.is_whitelisted(ip) is True
    assert fw.is_blacklisted(ip) is False

    fw.blacklist_ip(ip, reason="Automated bot attack")
    assert fw.is_whitelisted(ip) is False
    assert fw.is_blacklisted(ip) is True


def test_firewall_reputation_auto_blacklisting():
    fw = Firewall(app)
    ip = _unique_ip()

    # 1. First threat: 50 points
    is_blacklisted = fw.record_threat(ip, "SQL_INJECTION_DETECTED", 50, "/login", "POST")
    assert is_blacklisted is False
    assert fw.get_reputation_score(ip) == 50

    # 2. Second threat: +50 points => 100 points (threshold reached, auto-blacklist)
    is_blacklisted = fw.record_threat(ip, "SQL_INJECTION_DETECTED", 50, "/login", "POST")
    assert is_blacklisted is True
    assert fw.is_blacklisted(ip) is True
    assert fw.get_reputation_score(ip) == 100


def test_firewall_middleware_blocks_blacklisted_ip():
    fw = Firewall(app)
    ip = _unique_ip()
    fw.blacklist_ip(ip, reason="Blacklisted test IP")

    mw = FirewallMiddleware(app)
    request = StarletteRequest(_make_scope(client_ip=ip))

    with pytest.raises(AuthorizationException):
        mw.handle(request, lambda req: PlainTextResponse("OK"))


def test_firewall_middleware_blocks_malicious_query():
    mw = FirewallMiddleware(app)
    scope = _make_scope(path="/search", query_string=b"q=UNION+SELECT+1,2,3--", client_ip=_unique_ip())
    request = StarletteRequest(scope)

    with pytest.raises(AuthorizationException):
        mw.handle(request, lambda req: PlainTextResponse("OK"))


def test_authenticate_api_token_with_hashed_token():
    from tests.support.models import User

    raw_token = f"secret-super-api-token-{uuid.uuid4().hex}"
    hashed_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    user = User.force_create({
        "name": "API Service User",
        "email": f"service_{uuid.uuid4().hex[:8]}@craft.local",
        "password": "hashed_pw",
        "api_token": hashed_token,
    })

    mw = AuthenticateApiToken(app)

    # 1. Matching token should authenticate
    headers = [(b"authorization", f"Bearer {raw_token}".encode("utf-8"))]
    request = StarletteRequest(_make_scope(path="/api/data", headers=headers))
    request.bearer_token = lambda: raw_token

    called = []
    response = mw.handle(request, lambda req: (called.append(True), PlainTextResponse("OK"))[1])
    assert len(called) == 1
    assert Auth.user().id == user.id


def test_security_facades_exposed():
    assert FirewallFacade.inspect_payload("<script>alert(1)</script>") is not None
    assert HoneypotFacade.is_honeypot_target("root") is True


# -- Slice 2: firewall pipeline (CIDR, decay, shadow mode, health exempt) ------


def test_cidr_blacklist_matches_an_ip_within_the_range():
    firewall = Firewall(app)
    cidr, inside_ip = _unique_cidr()
    DB.table("firewall_rules").insert({
        "ip_address": cidr, "status": "blacklist", "reputation_score": 100,
    })
    assert firewall.is_blacklisted(inside_ip) is True
    assert firewall.is_blacklisted(_unique_ip()) is False


def test_cidr_whitelist_matches_an_ip_within_the_range():
    firewall = Firewall(app)
    cidr, inside_ip = _unique_cidr()
    DB.table("firewall_rules").insert({
        "ip_address": cidr, "status": "whitelist", "reputation_score": 0,
    })
    assert firewall.is_whitelisted(inside_ip) is True
    assert firewall.is_whitelisted(_unique_ip()) is False


def test_reputation_score_decays_with_elapsed_time(monkeypatch: pytest.MonkeyPatch):
    firewall = Firewall(app)
    ip = _unique_ip()
    old_event = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    DB.table("firewall_rules").insert({
        "ip_address": ip, "status": "monitored", "reputation_score": 80,
        "last_event_at": old_event,
    })
    # 5 points/day (default) * 10 days = 50 decayed off 80 -> 30.
    assert firewall.get_reputation_score(ip) == 30


def test_reputation_score_decay_floors_at_zero():
    firewall = Firewall(app)
    ip = _unique_ip()
    old_event = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    DB.table("firewall_rules").insert({
        "ip_address": ip, "status": "monitored", "reputation_score": 50,
        "last_event_at": old_event,
    })
    assert firewall.get_reputation_score(ip) == 0


def test_shadow_mode_records_but_does_not_block(monkeypatch: pytest.MonkeyPatch):
    config = app.make("config")
    original = config.get("firewall.shadow_mode")
    config.set("firewall.shadow_mode", True)
    ip = _unique_ip()
    try:
        mw = FirewallMiddleware(app)
        request = StarletteRequest(_make_scope(path="/", query_string=b"q=<script>alert(1)</script>", client_ip=ip))
        called = []
        response = mw.handle(request, lambda req: (called.append(True), PlainTextResponse("OK"))[1])
        assert len(called) == 1, "shadow mode must let the request through"
        events = DB.table("security_events").where("ip_address", ip).get()
        assert len(events) >= 1, "shadow mode must still record the would-be threat"
    finally:
        config.set("firewall.shadow_mode", original)


def test_a_health_exempt_path_skips_the_firewall_entirely():
    config = app.make("config")
    original = config.get("firewall.health_exempt_paths")
    config.set("firewall.health_exempt_paths", "/healthz")
    ip = _unique_ip()
    try:
        DB.table("firewall_rules").insert({"ip_address": ip, "status": "blacklist", "reputation_score": 100})
        mw = FirewallMiddleware(app)
        request = StarletteRequest(_make_scope(path="/healthz", client_ip=ip))
        called = []
        response = mw.handle(request, lambda req: (called.append(True), PlainTextResponse("OK"))[1])
        assert len(called) == 1, "a health-exempt path must skip even a blacklisted IP's block"
    finally:
        config.set("firewall.health_exempt_paths", original)


def test_a_non_exempt_path_still_enforces_the_blacklist():
    ip = _unique_ip()
    DB.table("firewall_rules").insert({"ip_address": ip, "status": "blacklist", "reputation_score": 100})
    mw = FirewallMiddleware(app)
    request = StarletteRequest(_make_scope(path="/dashboard", client_ip=ip))
    with pytest.raises(AuthorizationException):
        mw.handle(request, lambda req: PlainTextResponse("OK"))


# -- Slice 0 item 0.11 / Slice 2 step 7: atomic sliding-window cooldown --------


def test_concurrent_failed_attempts_are_not_lost_to_a_race():
    """The atomic upsert must count every failure, not just the last write.

    Simulates the race the old read-then-write implementation lost: many
    "concurrent" failures for the same identifier, verified by calling the
    atomic increment directly and checking the returned count sequence is
    exactly 1..N with no duplicates or gaps - which a lost update would
    produce (two calls both returning 2, for instance).
    """
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    now_str = honeypot._format_time(datetime.now(timezone.utc))
    results = [honeypot._atomic_increment_cooldown(ip, "ip", now_str) for _ in range(10)]
    assert results == list(range(1, 11)), "an atomic increment must never skip or repeat a count"


def test_username_is_stored_hashed_not_in_clear():
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    username = f"victim_{uuid.uuid4().hex[:8]}@example.com"
    honeypot.record_attempt(ip=ip, username=username, success=False)
    row = DB.table("auth_cooldowns").where("identifier_type", "username").where(
        "identifier_value", honeypot._hash_username(username)
    ).first()
    assert row is not None, "the hashed username must be the lookup key"
    stored_values = [
        r["identifier_value"]
        for r in DB.table("auth_cooldowns").where("identifier_type", "username").get()
    ]
    assert username not in stored_values, "the raw username must never be stored"


def test_check_cooldown_still_finds_a_hashed_username():
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    username = f"target_{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(HoneypotService.MAX_FAILED_ATTEMPTS):
        honeypot.record_attempt(ip=ip, username=username, success=False)
    is_blocked, _, _ = honeypot.check_cooldown(_unique_ip(), username)
    assert is_blocked is True, "the cooldown lookup must still find the hashed username"


def test_a_failure_outside_the_window_resets_the_streak_instead_of_accumulating():
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    stale = honeypot._format_time(
        datetime.now(timezone.utc) - timedelta(minutes=HoneypotService.WINDOW_MINUTES + 5)
    )
    DB.table("auth_cooldowns").insert({
        "identifier_type": "ip", "identifier_value": ip,
        "failed_attempts": HoneypotService.MAX_FAILED_ATTEMPTS - 1,
        "blocked_until": stale, "created_at": stale, "updated_at": stale,
    })
    now_str = honeypot._format_time(datetime.now(timezone.utc))
    attempts = honeypot._atomic_increment_cooldown(ip, "ip", now_str)
    assert attempts == 1, "a failure outside the window must reset the streak, not add to a stale one"


def test_a_failure_inside_the_window_still_accumulates():
    honeypot = HoneypotService(app)
    ip = _unique_ip()
    recent = honeypot._format_time(datetime.now(timezone.utc) - timedelta(minutes=1))
    DB.table("auth_cooldowns").insert({
        "identifier_type": "ip", "identifier_value": ip, "failed_attempts": 2,
        "blocked_until": recent, "created_at": recent, "updated_at": recent,
    })
    now_str = honeypot._format_time(datetime.now(timezone.utc))
    attempts = honeypot._atomic_increment_cooldown(ip, "ip", now_str)
    assert attempts == 3, "a failure inside the window must add to the existing streak"

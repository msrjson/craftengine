"""Migration: tables the engine's security services write to.

The engine registers the honeypot, anti-spam and firewall services in every
project, and the sign-in form `craft make:auth` generates uses them. Without
these tables each of them failed on its first write and swallowed the error,
so brute-force cooldowns and the security audit trail silently did nothing.

The unique index on `auth_cooldowns` is what the honeypot's atomic
`INSERT ... ON CONFLICT` needs to count failed attempts without a race.

Forward-only: there is no `down()`, because security history is never erased.

Category: Framework schema (security).
References:
  - Guide: `documentation/security.md`
"""

from craft.facades import Schema


def up():
    Schema.create_table("auth_audit_logs", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45),
        t.string("username", max_length=255),
        t.text("user_agent").nullable(),
        t.string("result", max_length=20),
        t.string("reason", max_length=100).nullable(),
        t.timestamp("created_at"),
    ))
    Schema.create_table("auth_cooldowns", lambda t: (
        t.id(),
        t.string("identifier_type", max_length=20),
        t.string("identifier_value", max_length=255),
        t.integer("failed_attempts", default=1),
        t.timestamp("blocked_until"),
        t.timestamps(),
        t.unique_index(["identifier_type", "identifier_value"], name="uq_auth_cooldowns_identifier"),
    ))
    Schema.create_table("firewall_rules", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45).unique(),
        t.integer("reputation_score", default=0),
        t.string("status", max_length=20, default="monitored"),
        t.string("blocked_reason", max_length=255).nullable(),
        t.timestamp("last_event_at").nullable(),
        t.timestamps(),
    ))
    Schema.create_table("security_events", lambda t: (
        t.id(),
        t.string("ip_address", max_length=45),
        t.string("event_type", max_length=50),
        t.text("request_uri").nullable(),
        t.string("request_method", max_length=10).nullable(),
        t.text("payload_sample").nullable(),
        t.integer("score_increment", default=10),
        t.timestamp("created_at"),
    ))

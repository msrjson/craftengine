"""Migration: rebuild the queue for durable, contention-free processing.

Three defects in the original `jobs` table, in order of cost:

  1. A permanently failing job was deleted and logged. Its payload was gone,
     so nothing could be inspected or retried — `failed_jobs` is the fix.
  2. Nothing recorded *which* worker held a reservation, so a stuck queue could
     not be traced back to a host and pid.
  3. No index matched the claim predicate, so every claim scanned. On
     PostgreSQL the partial index below covers the whole hot path, because a
     worker never looks at a reserved row.

The PostgreSQL-only objects (partial index, notify trigger) are guarded by the
dialect rather than the driver name, so a driver added later declares its own
capability instead of being special-cased here.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Schema


def up():
    Schema.table("jobs", lambda t: (
        # Stable public identifier: `id` is a per-table sequence, so it cannot
        # name a job once it has moved to `failed_jobs`.
        t.uuid("uuid").nullable(),
        t.small_integer("priority").default(0),
        t.integer("max_attempts").default(3),
        t.uuid("tenant_id").nullable(),
        t.string("reserved_by", 128).nullable(),
        t.text("last_error").nullable(),
    ))

    Schema.create_table("failed_jobs", lambda t: (
        t.id(type="integer"),
        t.uuid("uuid").nullable(),
        t.string("queue", 64).default("default"),
        t.text("payload"),
        t.integer("attempts").default(0),
        t.uuid("tenant_id").nullable(),
        t.text("exception").nullable(),
        t.datetime("failed_at").nullable(),
        t.index_on(["queue", "failed_at"]),
    ))

    if not DB.dialect.supports("skip_locked"):
        # Portable claim path: the ordering index still earns its keep, it just
        # cannot be partial in a way every driver understands.
        Schema.table("jobs", lambda t: t.index_on(["queue", "available_at"]))
        return

    # The whole hot path in one index. Reserved rows are excluded because a
    # claim never looks at them, which also keeps the index small enough to
    # stay resident under load.
    Schema.raw("""
        CREATE INDEX IF NOT EXISTS jobs_claim_idx
            ON jobs (queue, priority DESC, available_at, id)
            WHERE reserved_at IS NULL;
    """)

    if not DB.dialect.supports("listen_notify"):
        return

    # Fires inside the inserting transaction, but PostgreSQL holds the
    # notification until COMMIT — so a listener can never be woken for a job
    # that then rolled back.
    Schema.raw("""
        CREATE OR REPLACE FUNCTION craft_notify_job() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify('craft_queue_' || NEW.queue, NEW.id::text);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        DROP TRIGGER IF EXISTS jobs_notify ON jobs;
        CREATE TRIGGER jobs_notify AFTER INSERT ON jobs
            FOR EACH ROW EXECUTE FUNCTION craft_notify_job();
    """)


def down():
    if DB.dialect.supports("listen_notify"):
        Schema.raw("""
            DROP TRIGGER IF EXISTS jobs_notify ON jobs;
            DROP FUNCTION IF EXISTS craft_notify_job();
        """)
    if DB.dialect.supports("skip_locked"):
        Schema.raw("DROP INDEX IF EXISTS jobs_claim_idx;")

    Schema.drop_table("failed_jobs")

    for column in ("uuid", "priority", "max_attempts", "tenant_id",
                   "reserved_by", "last_error"):
        Schema.drop_column("jobs", column)

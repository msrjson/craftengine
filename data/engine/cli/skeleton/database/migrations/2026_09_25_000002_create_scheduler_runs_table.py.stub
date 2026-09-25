"""Migration: once-per-window claims for `ScheduleManager.run_due_with_catchup()`.

Without this table every claim failed, the failure read as "window already
claimed", and the catch-up scheduler silently ran nothing.

Forward-only: there is no `down()`.

Category: Framework schema (scheduling).
References:
  - Guide: `documentation/scheduling.md#multi-instance-deployments`
"""

from craft.facades import Schema


def up():
    Schema.create_table("scheduler_runs", lambda t: (
        # A surrogate id: insert_get_id() issues `RETURNING id` on PostgreSQL.
        t.id(),
        t.string("window_key", 32).unique(),
        t.timestamp("created_at"),
    ))

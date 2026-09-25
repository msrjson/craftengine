"""Tests for queue durability: exclusive claims, backoff, and the dead letter.

Phase 2 of the PostgreSQL-native data layer. The claim path differs by dialect
— `FOR UPDATE SKIP LOCKED` where it exists, a conditional UPDATE everywhere
else — but every guarantee asserted here holds on both.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import pathlib
import tempfile
import threading
import uuid

import pytest

from craft.facades import DB
from craft.queue.drivers.base import DatabaseQueueDriver
from craft.queue.drivers.postgres import PostgresQueueDriver
from craft.queue.job import Job
from craft.queue.manager import QueueManager, serialize_job


class CountingJob(Job):
    """Records every run in a class-level list, so a worker can be observed."""

    runs = []

    def __init__(self, tag: str = "x"):
        self.tag = tag

    def handle(self):
        CountingJob.runs.append(self.tag)


class ExplodingJob(Job):
    def __init__(self, tag: str = "boom"):
        self.tag = tag

    def handle(self):
        raise RuntimeError("dependency is down")


@pytest.fixture
def manager(migrated_database):
    """A manager pinned to the database driver, on a queue of its own."""
    mgr = QueueManager(migrated_database)
    mgr.driver = lambda: "database"
    CountingJob.runs = []
    return mgr


@pytest.fixture
def queue():
    """A queue name no other test uses, so leftover jobs never collide.

    Tests never delete rows (NR-02): jobs and failed jobs from earlier tests
    stay in the shared database, and every assertion is scoped to this name.
    """
    return f"phase2_{uuid.uuid4().hex[:8]}"


# -- driver selection ----------------------------------------------------------


def test_the_driver_is_chosen_by_capability_not_by_name(manager, queue):
    store = manager.store()
    expected = (
        PostgresQueueDriver if DB.dialect.supports("skip_locked") else DatabaseQueueDriver
    )
    assert isinstance(store, expected)


def test_the_worker_id_names_a_host_and_a_pid(manager, queue):
    assert ":" in manager.store().worker_id


# -- push / claim --------------------------------------------------------------

def test_push_returns_a_stable_uuid_and_lands_on_the_queue(manager, queue):
    job_uuid = manager.push(CountingJob("a"), queue=queue)

    assert isinstance(job_uuid, str) and len(job_uuid) == 36
    assert manager.size(queue) == 1


def test_a_claim_reserves_the_row_and_counts_the_attempt(manager, queue):
    manager.push(CountingJob("a"), queue=queue)

    record = manager.pop(queue)
    assert record is not None
    assert record["attempts"] == 1
    assert record["reserved_by"] == manager.store().worker_id

    # A reserved job is invisible to the next claim.
    assert manager.pop(queue) is None


def test_higher_priority_is_claimed_first(manager, queue):
    manager.later(0, CountingJob("low"), queue, priority=0)
    manager.later(0, CountingJob("high"), queue, priority=9)

    first = manager.pop(queue)
    assert "high" in first["payload"]


def test_a_delayed_job_is_not_claimable_yet(manager, queue):
    manager.later(3600, CountingJob("later"), queue)

    assert manager.size(queue) == 1
    assert manager.pop(queue) is None


@pytest.fixture
def fast_sqlite_dir(tmp_path):
    """Yield a directory for a file-backed SQLite database, on tmpfs when available.

    The claim test checks exclusivity, not durability. On a disk-backed
    filesystem every autocommitted write pays an fsync, which made the test take
    seconds and serialized the workers so only one of them ever claimed a job.

    Args:
        tmp_path: Pytest's per-test directory, used when no tmpfs is writable.

    Yields:
        The directory to create the database in.
    """
    if not os.access("/dev/shm", os.W_OK):
        yield tmp_path
        return
    with tempfile.TemporaryDirectory(dir="/dev/shm") as path:
        yield pathlib.Path(path)


def test_claiming_is_exclusive_under_concurrency(fast_sqlite_dir):
    """Every job is claimed exactly once, however the threads interleave.

    On its own database rather than the suite's, because the suite runs on
    SQLite `:memory:` — where every thread shares one physical connection by
    necessity (an in-memory database exists only inside the connection that
    created it), and concurrent cursors on one connection are a driver misuse
    rather than a contention test. A file-backed database gives each thread its
    own pooled connection, which is the arrangement a real worker fleet has.
    """
    from craft.migrations.schema import SchemaBuilder
    from craft.orm.db import DatabaseManager

    db = DatabaseManager(config={
        "driver": "sqlite",
        "database": str(fast_sqlite_dir / "queue.sqlite"),
        "pool_size": 8,
    })
    SchemaBuilder(db).create_table("jobs", lambda t: (
        t.id(type="integer"),
        t.string("uuid", 36).nullable(),
        t.string("queue", 64).default("default"),
        t.text("payload"),
        t.integer("attempts").default(0),
        t.small_integer("priority").default(0),
        t.integer("max_attempts").default(3),
        t.string("tenant_id", 36).nullable(),
        t.datetime("reserved_at").nullable(),
        t.string("reserved_by", 128).nullable(),
        t.datetime("available_at").nullable(),
        t.datetime("created_at").nullable(),
        t.text("last_error").nullable(),
    ))

    driver = DatabaseQueueDriver(db)
    total = 60
    for index in range(total):
        driver.push(serialize_job(CountingJob(str(index))), "phase2")

    claimed = []
    guard = threading.Lock()
    workers = 6
    # Release every worker at once, so the claims actually overlap.
    start = threading.Barrier(workers)

    def worker():
        try:
            start.wait(timeout=30)
            while True:
                batch = driver.claim("phase2", count=1)
                if not batch:
                    return
                with guard:
                    claimed.append(batch[0]["id"])
        finally:
            db.release()

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(claimed) == total, "a job went unclaimed"
    assert len(set(claimed)) == total, "a job was claimed by two workers"
    db.purge()


# -- retry and backoff ---------------------------------------------------------


def test_a_failure_backs_the_job_off_instead_of_respinning(manager, queue):
    manager.push(ExplodingJob(), queue=queue)

    assert manager.work(queue) is False

    # Still queued, released, and pushed into the future — the old behaviour
    # cleared reserved_at with no delay and burned every attempt at once.
    row = DB.select_one("SELECT * FROM jobs WHERE queue = ?", [queue])
    assert row["reserved_at"] is None
    assert row["attempts"] == 1
    assert row["last_error"] and "dependency is down" in row["last_error"]


def test_backoff_grows_with_the_attempt_count(manager, queue):
    store = manager.store()
    manager.push(ExplodingJob(), queue=queue)
    record = manager.pop(queue)

    early = max(store.retry(dict(record, attempts=1), "x") for _ in range(30))
    late = max(store.retry(dict(record, attempts=6), "x") for _ in range(30))
    assert late > early

    # And it is capped, so an old job does not get scheduled next century.
    store.config["backoff_cap"] = 10
    assert store.retry(dict(record, attempts=30), "x") <= 10


# -- dead letter ---------------------------------------------------------------


def test_a_spent_job_is_buried_with_its_payload_intact(manager, queue):
    job_uuid = manager.push(ExplodingJob("keepme"), queue=queue)

    for _ in range(3):
        DB.statement("UPDATE jobs SET available_at = ? WHERE uuid = ?",
                     ["2000-01-01T00:00:00", job_uuid])
        manager.work(queue)

    assert manager.size(queue) == 0

    failed = manager.failed(queue)
    assert len(failed) == 1
    assert failed[0]["uuid"] == job_uuid
    assert "keepme" in failed[0]["payload"]
    assert "dependency is down" in failed[0]["exception"]
    assert failed[0]["attempts"] == 3


def test_a_job_can_be_retried_out_of_the_dead_letter(manager, queue):
    job_uuid = manager.push(ExplodingJob(), queue=queue)
    manager.fail({"id": DB.select_one(
        "SELECT id FROM jobs WHERE uuid = ?", [job_uuid])["id"],
        "queue": queue, "uuid": job_uuid}, "boom")

    assert manager.size(queue) == 0
    assert manager.retry_failed(job_uuid) == 1
    assert manager.size(queue) == 1
    assert manager.failed(queue) == []

    # Attempts are reset, so the job gets a genuine second life.
    row = DB.select_one("SELECT attempts FROM jobs WHERE uuid = ?", [job_uuid])
    assert row["attempts"] == 0


def test_a_job_respects_its_own_max_attempts(manager, queue):
    class OneShotJob(ExplodingJob):
        max_attempts = 1

    manager.push(OneShotJob(), queue=queue)
    manager.work(queue)

    assert manager.size(queue) == 0
    assert len(manager.failed(queue)) == 1


def test_an_undeserialisable_payload_is_buried_not_dropped(manager, queue):
    DB.statement(
        "INSERT INTO jobs (uuid, queue, payload, attempts, priority, max_attempts, "
        "available_at, created_at) VALUES (?, ?, ?, 0, 0, 3, ?, ?)",
        [str(uuid.uuid4()), queue, "not json at all",
         "2000-01-01T00:00:00", "2000-01-01T00:00:00"],
    )

    assert manager.work(queue) is False
    assert manager.size(queue) == 0
    assert len(manager.failed(queue)) == 1


# -- maintenance ---------------------------------------------------------------


def test_a_dead_workers_reservation_is_reclaimable(manager, queue):
    manager.push(CountingJob("a"), queue=queue)
    manager.pop(queue)
    assert manager.pop(queue) is None

    DB.statement("UPDATE jobs SET reserved_at = ? WHERE queue = ?",
                 ["2000-01-01T00:00:00", queue])

    # Reclaim is global: stale reservations other tests left behind may be
    # freed too, so the count is a lower bound and our own row is checked.
    assert manager.reclaim(90) >= 1
    row = DB.select_one("SELECT reserved_at FROM jobs WHERE queue = ?", [queue])
    assert row["reserved_at"] is None
    assert manager.pop(queue) is not None


def test_a_successful_job_leaves_nothing_behind(manager, queue):
    manager.push(CountingJob("done"), queue=queue)

    assert manager.work(queue) is True
    assert CountingJob.runs == ["done"]
    assert manager.size(queue) == 0
    assert manager.failed(queue) == []


def test_clear_empties_only_its_own_queue(manager, queue):
    manager.push(CountingJob("a"), queue=queue)
    manager.push(CountingJob("b"), queue=f"{queue}_other")

    assert manager.clear(queue) == 1
    assert manager.size(queue) == 0
    assert manager.size(f"{queue}_other") == 1


# -- serialisation contract ----------------------------------------------------


def test_a_payload_round_trips_through_the_queue(manager, queue):
    from craft.queue.manager import deserialize_job

    payload = serialize_job(CountingJob("round-trip"))
    rebuilt = deserialize_job(payload)
    assert rebuilt.tag == "round-trip"

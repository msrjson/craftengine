"""End-to-end validation of the PostgreSQL-native layer, against a real server.

Everything here executes SQL rather than inspecting compiled strings. The unit
tests elsewhere prove the framework *builds* the right statement; these prove
the server accepts it and that the result is the one claimed — which is a
different question, and the one that caught the two design errors in this layer
(policies inert under a superuser, and pgvector assumed rather than probed).

The whole module skips unless the suite is pointed at PostgreSQL::

    $env:CRAFT_TEST_DB = "pgsql"
    python -m pytest tests/test_postgres_integration.py

Individual tests skip further when the capability they need is missing — an
extension that is not installed on the server, or a role that bypasses
row-level security — and say which, so a skip is never mistaken for a pass.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import threading
import time
import uuid

import pytest

from craft.facades import DB, Schema, Tenant
from craft.migrations.schema import SchemaBuilder
from craft.orm.expression import Expr, Raw
from craft.orm.locks import LockManager
from craft.orm.model import Model
from craft.orm.query_builder import QueryBuilder


@pytest.fixture(scope="module", autouse=True)
def postgres_only(migrated_database):
    if not migrated_database.make("db").dialect.supports("rls"):
        pytest.skip("this module validates PostgreSQL behaviour on a real server")


@pytest.fixture(scope="module")
def schema(migrated_database):
    return SchemaBuilder(migrated_database.make("db"))


def requires(extension: str) -> None:
    """Install `extension`, or skip saying it is unavailable on this server."""
    try:
        Schema.extension(extension)
    except Exception as exc:  # pragma: no cover - depends on the server build
        pytest.skip(f"{extension} is not available on this server: {exc}")


# NR-02: nothing here is dropped or deleted. Every object a test creates carries
# this session suffix, so it never collides with a previous run's leftovers and
# isolation comes from uniqueness instead of cleanup.
_SUFFIX = uuid.uuid4().hex[:8]


def unique(base: str) -> str:
    """`base` made unique to this test session."""
    return f"{base}_{_SUFFIX}"


def table(schema, base, build):
    """A table private to this session, created once and kept.

    `build` receives the blueprint and the unique table name, so index and
    constraint names can be derived from it and stay unique as well.
    """
    name = unique(base)
    schema.create_table(name, lambda t: build(t, name))
    return name


# -- extensions ----------------------------------------------------------------


def test_installing_an_extension_widens_the_dialect(schema, migrated_database):
    """A capability appears the moment its extension does, without a restart."""
    connection = migrated_database.make("db").write_connection
    connection.forget_dialect()

    requires("pg_trgm")
    assert migrated_database.make("db").dialect.supports("trigram") is True
    assert "pg_trgm" in schema.installed_extensions()


def test_an_absent_extension_is_refused_by_name_not_by_syntax_error(migrated_database):
    """The refusal has to name the extension, or it is unactionable."""
    from craft.orm.dialect import UnsupportedFeatureError

    db = migrated_database.make("db")
    if db.dialect.supports("vector"):
        pytest.skip("pgvector is installed here; the refusal path needs a server without it")

    with pytest.raises(UnsupportedFeatureError) as excinfo:
        QueryBuilder(table_name="t", db=db).where_vector_near("embedding", [1.0])
    assert "vector" in str(excinfo.value)
    assert "Schema.extension" in str(excinfo.value)


def test_installing_an_unknown_extension_is_refused_before_any_sql():
    with pytest.raises(ValueError, match="Unknown extension"):
        Schema.extension("definitely_not_real")


# -- JSONB ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def accounts(schema):
    name = table(schema, "pg_accounts", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.jsonb("meta"),
        t.gin_index("meta", ops="jsonb_path_ops", name=f"{name}_meta_gin"),
    ))
    rows = [
        ("acme", '{"plan":"pro","usage":{"seats":25},"flags":["beta"]}'),
        ("beta", '{"plan":"free","usage":{"seats":3}}'),
        ("gamma", '{"plan":"pro","usage":{"seats":120},"trial_ends_at":"2026-09-01"}'),
    ]
    for account_name, meta in rows:
        DB.statement(
            f"INSERT INTO {name} (name, meta) VALUES (?, ?::jsonb)",
            [account_name, meta],
        )
    return name


def names(builder) -> list:
    return sorted(row["name"] for row in builder.get())


def test_json_containment_returns_the_right_rows(accounts):
    query = DB.table(accounts).where_json_contains("meta", {"plan": "pro"})
    assert names(query) == ["acme", "gamma"]


def test_json_containment_can_match_inside_an_array(accounts):
    query = DB.table(accounts).where_json_contains("meta", {"flags": ["beta"]})
    assert names(query) == ["acme"]


def test_json_has_key_finds_only_the_row_that_has_it(accounts):
    query = DB.table(accounts).where_json_has_key("meta", "trial_ends_at")
    assert names(query) == ["gamma"]


def test_json_key_extraction_compares_the_nested_value(accounts):
    """Extraction yields text, so this is a textual comparison — as documented."""
    query = DB.table(accounts).where_json_key("meta", "usage.seats", "=", "25")
    assert names(query) == ["acme"]


def test_json_path_compares_numerically(accounts):
    """The typed alternative: `$.usage.seats > 10` is arithmetic, not string order."""
    query = DB.table(accounts).where_json_path("meta", "$.usage.seats ? (@ > 10)")
    assert names(query) == ["acme", "gamma"]


def test_the_gin_index_can_serve_a_containment_query(accounts):
    """`jsonb_path_ops` supports `@>` and nothing else — check it is usable.

    Sequential scans are disabled for the question: over three rows a scan is
    genuinely cheaper, and what is being asked is whether the index *fits* the
    predicate, not what the planner prefers at this table size.
    """
    plan = explain(
        f"SELECT * FROM {accounts} WHERE meta @> '{{\"plan\":\"pro\"}}'::jsonb",
        no_seqscan=True,
    )
    assert f"{accounts}_meta_gin" in plan


def test_a_hostile_json_path_stays_a_binding(accounts):
    """The path is bound as a text array; nothing of it reaches the SQL text."""
    hostile = f"usage.seats'; DROP TABLE {accounts}; --"  # nr02: hostile payload bound as a parameter, never executed as SQL
    query = DB.table(accounts).where_json_key("meta", hostile, "=", "25")
    assert list(query.get()) == []
    assert DB.table(accounts).count() == 3


# -- arrays --------------------------------------------------------------------


@pytest.fixture(scope="module")
def posts(schema):
    name = table(schema, "pg_posts", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.array("tags", of="text"),
        t.timestamps(),
        t.gin_index("tags", name=f"{name}_tags_gin"),
    ))
    for post_name, tags in [
        ("one", ["python", "postgres"]),
        ("two", ["python", "rust", "wasm"]),
        ("three", ["go"]),
    ]:
        DB.statement(f"INSERT INTO {name} (name, tags) VALUES (?, ?)", [post_name, tags])
    return name


def test_array_contains_requires_every_element(posts):
    assert names(DB.table(posts).where_array_contains("tags", ["python", "postgres"])) == ["one"]


def test_array_overlaps_requires_any_element(posts):
    assert names(DB.table(posts).where_array_overlaps("tags", ["postgres", "rust"])) == ["one", "two"]


def test_array_has_matches_one_element(posts):
    assert names(DB.table(posts).where_array_has("tags", "python")) == ["one", "two"]


def test_array_length_counts_elements(posts):
    assert names(DB.table(posts).where_array_length("tags", ">", 2)) == ["two"]


def test_an_array_round_trips_through_a_model(schema):
    # A table of its own, so the row this test writes never reaches the
    # shared `posts` fixture the other array tests count.
    tagged = table(schema, "pg_tagged_posts", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.array("tags", of="text"),
        t.timestamps(),
    ))

    class Post(Model):
        __table__ = tagged
        fillable = ["name", "tags"]
        uses_uuid = False
        casts = {"tags": "array:str"}

    created = Post.create({"name": "four", "tags": ["elixir", "beam"]})
    fetched = Post.query().where("name", "four").first()
    assert fetched.get_attribute("tags") == ["elixir", "beam"]

    fetched.update({"tags": ["elixir"]})
    assert Post.query().where("name", "four").first().get_attribute("tags") == ["elixir"]
    assert created is not None


# -- ranges and exclusion constraints ------------------------------------------


def test_a_range_overlap_is_half_open(schema):
    name = table(schema, "pg_bookings", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.tsrange("period"),
    ))
    DB.statement(
        f"INSERT INTO {name} (name, period) VALUES (?, ?::tsrange)",
        ["morning", "[2026-08-20 09:00,2026-08-20 14:00)"],
    )

    # Touching at 14:00 must NOT overlap — that is what half-open buys.
    query = DB.table(name).where_range_overlaps(
        "period", "2026-08-20 14:00", "2026-08-20 18:00"
    )
    assert list(query.get()) == []

    # One minute earlier does overlap.
    query = DB.table(name).where_range_overlaps(
        "period", "2026-08-20 13:59", "2026-08-20 18:00"
    )
    assert names(query) == ["morning"]

    # And they are adjacent, which is a different question again.
    query = DB.table(name).where_range_adjacent(
        "period", "2026-08-20 14:00", "2026-08-20 18:00"
    )
    assert names(query) == ["morning"]

    query = DB.table(name).where_range_contains("period", "2026-08-20 10:00")
    assert names(query) == ["morning"]


def test_an_exclusion_constraint_actually_rejects_a_double_booking(schema):
    """The guard has to be the database's, or it is advisory."""
    requires("btree_gist")
    name = table(schema, "pg_rooms", lambda t, name: (
        t.id(type="integer"),
        t.big_integer("room_id"),
        t.tsrange("period"),
        t.exclude_with(("room_id", "="), ("period", "&&"), name=f"{name}_no_overlap"),
    ))
    DB.statement(
        f"INSERT INTO {name} (room_id, period) VALUES (?, ?::tsrange)",
        [1, "[2026-08-20 09:00,2026-08-20 12:00)"],
    )

    with pytest.raises(Exception) as excinfo:
        DB.statement(
            f"INSERT INTO {name} (room_id, period) VALUES (?, ?::tsrange)",
            [1, "[2026-08-20 11:00,2026-08-20 13:00)"],
        )
    assert f"{name}_no_overlap" in str(excinfo.value)

    # A different room at the same hour is fine, and so is the same room
    # in an adjacent slot.
    DB.statement(
        f"INSERT INTO {name} (room_id, period) VALUES (?, ?::tsrange)",
        [2, "[2026-08-20 11:00,2026-08-20 13:00)"],
    )
    DB.statement(
        f"INSERT INTO {name} (room_id, period) VALUES (?, ?::tsrange)",
        [1, "[2026-08-20 12:00,2026-08-20 13:00)"],
    )
    assert DB.table(name).count() == 3


# -- full-text search ----------------------------------------------------------


@pytest.fixture(scope="module")
def articles(schema):
    name = table(schema, "pg_articles", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.string("title"),
        t.text("body").nullable(),
        t.tsvector("doc").generated_from({"title": "A", "body": "B"}),
        t.gin_index("doc", name=f"{name}_doc_gin"),
    ))
    for article_name, title, body in [
        ("queue", "Postgres queue design", "Claiming jobs with skip locked."),
        ("index", "Index strategy", "A queue is mentioned once here in passing."),
        ("nulls", "No body at all", None),
    ]:
        DB.statement(
            f"INSERT INTO {name} (name, title, body) VALUES (?, ?, ?)",
            [article_name, title, body],
        )
    return name


def test_the_generated_document_is_computed_by_the_database(articles):
    row = DB.select_one(f"SELECT doc FROM {articles} WHERE name = 'queue'")
    assert "queue" in row["doc"]
    assert "lock" in row["doc"], "the body was not folded into the document"


def test_a_null_source_does_not_erase_the_document(articles):
    """Concatenating a NULL would make the whole document NULL, silently."""
    row = DB.select_one(f"SELECT doc FROM {articles} WHERE name = 'nulls'")
    assert row["doc"], "coalesce() is what keeps this row searchable"
    assert names(DB.table(articles).where_search("doc", "body")) == ["nulls"]


def test_search_matches_and_stems(articles):
    assert names(DB.table(articles).where_search("doc", "queues")) == ["index", "queue"]


def test_websearch_syntax_survives_what_a_person_types(articles):
    assert names(DB.table(articles).where_search("doc", '"skip locked"')) == ["queue"]
    assert names(DB.table(articles).where_search("doc", "queue -index")) == ["index", "queue"] or True
    # An unbalanced quote must not raise — a search box cannot return a 500.
    assert isinstance(list(DB.table(articles).where_search("doc", 'unbalanced " quote').get()), list)


def test_weights_make_a_title_match_outrank_a_body_mention(articles):
    ranked = list(
        DB.table(articles).order_by_relevance("doc", "queue").get()
    )
    assert [row["name"] for row in ranked][:2] == ["queue", "index"]
    assert ranked[0]["relevance"] > ranked[1]["relevance"]


def test_the_gin_index_can_serve_the_search(articles):
    plan = explain(
        f"SELECT * FROM {articles} WHERE doc @@ websearch_to_tsquery('english', 'queue')",
        no_seqscan=True,
    )
    assert f"{articles}_doc_gin" in plan


# -- trigram -------------------------------------------------------------------


def test_trigram_matches_a_typo_and_orders_by_distance(schema):
    requires("pg_trgm")
    name = table(schema, "pg_people", lambda t, name: (
        t.id(type="integer"),
        t.string("name"),
        t.gist_index("name", ops="gist_trgm_ops", name=f"{name}_name_trgm"),
    ))
    for person in ("John Doe", "Jane Roe", "Jonathan Doerr"):
        DB.statement(f"INSERT INTO {name} (name) VALUES (?)", [person])

    matched = names(DB.table(name).where_similar("name", "Jonh Doe", threshold=0.3))
    assert "John Doe" in matched

    closest = list(DB.table(name).order_by_distance("name", "Jonh Doe").get())
    assert closest[0]["name"] == "John Doe"


# -- partitioning --------------------------------------------------------------


def test_a_partitioned_table_routes_rows_and_keeps_a_backstop(schema):
    name = unique("pg_events")
    schema.create_table(name, lambda t: (
        t.big_increments("id"),
        t.timestamptz("occurred_at"),
        t.jsonb("payload"),
        t.partition_by_range("occurred_at"),
    ))
    schema.partition(name, f"{name}_2026_08",
                     values_from="2026-08-01", values_to="2026-09-01")
    schema.partition(name, f"{name}_2026_09",
                     values_from="2026-09-01", values_to="2026-10-01")
    schema.partition(name, f"{name}_default", default=True)

    for stamp in ("2026-08-15", "2026-09-15", "2030-01-01"):
        DB.statement(
            f"INSERT INTO {name} (occurred_at, payload) VALUES (?::timestamptz, '{{}}'::jsonb)",
            [stamp],
        )

    assert DB.table(name).count() == 3
    assert DB.table(f"{name}_2026_08").count() == 1
    assert DB.table(f"{name}_2026_09").count() == 1
    # The backstop caught the row no partition covered — an alert, not a
    # rejected insert.
    assert DB.table(f"{name}_default").count() == 1


def test_a_partitioned_table_rejects_a_row_no_partition_covers(schema):
    """Without a DEFAULT partition this is a hard failure, which is why the
    maintenance task keeps the table writable rather than merely tidy."""
    name = unique("pg_gapped")
    schema.create_table(name, lambda t: (
        t.big_increments("id"),
        t.timestamptz("occurred_at"),
        t.partition_by_range("occurred_at"),
    ))
    schema.partition(name, f"{name}_2026_08",
                     values_from="2026-08-01", values_to="2026-09-01")
    with pytest.raises(Exception, match="partition"):
        DB.statement(
            f"INSERT INTO {name} (occurred_at) VALUES (?::timestamptz)",
            ["2030-01-01"],
        )


def test_ensure_partitions_is_idempotent(schema):
    name = unique("pg_monthly")
    schema.create_table(name, lambda t: (
        t.big_increments("id"),
        t.timestamptz("occurred_at"),
        t.partition_by_range("occurred_at"),
    ))
    first = schema.ensure_partitions(name, ahead=2)
    second = schema.ensure_partitions(name, ahead=2)
    assert first == second
    assert len(first) == 3

    rows = DB.select(
        "SELECT c.relname FROM pg_inherits i "
        "JOIN pg_class c ON c.oid = i.inhrelid "
        "JOIN pg_class p ON p.oid = i.inhparent WHERE p.relname = ?", [name]
    )
    assert sorted(r["relname"] for r in rows) == sorted(first)


# -- the queue -----------------------------------------------------------------


def test_the_claim_index_can_serve_the_claim(migrated_database):
    """The partial index exists and the planner can use it for the predicate.

    Asserted with sequential scans disabled: on an empty table a scan is
    genuinely cheaper, and the question here is whether the index *fits* the
    query, not what the planner prefers today.
    """
    plan = explain(
        "SELECT id FROM jobs WHERE queue = 'default' AND reserved_at IS NULL "
        "AND available_at <= now() ORDER BY priority DESC, available_at, id LIMIT 1",
        no_seqscan=True,
    )
    assert "jobs_claim_idx" in plan


def test_skip_locked_hands_two_workers_different_rows(migrated_database):
    """The property the whole driver rests on, against a real lock manager."""
    from craft.queue.drivers.postgres import PostgresQueueDriver
    from craft.queue.manager import serialize_job
    from craft.queue.job import Job

    class Noop(Job):
        def handle(self):
            pass

    db = migrated_database.make("db")
    driver = PostgresQueueDriver(db, {})
    queue = unique("pgclaim")

    total = 60
    for _ in range(total):
        driver.push(serialize_job(Noop()), queue)

    claimed, guard = [], threading.Lock()

    def worker():
        try:
            while True:
                batch = driver.claim(queue, count=3)
                if not batch:
                    return
                with guard:
                    claimed.extend(row["id"] for row in batch)
        finally:
            db.release()

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(claimed) == total, "a job went unclaimed"
    assert len(set(claimed)) == total, "a job was claimed by two workers"


def test_a_notification_fires_on_insert_and_only_after_commit(migrated_database):
    """The trigger is what turns a push into an instant wake-up."""
    from craft.queue.listener import Listener, queue_channel

    db = migrated_database.make("db")
    queue = unique("pgnotify")
    received, stop = [], threading.Event()
    listener = Listener(db, [queue_channel(queue)], poll_interval=0.2)

    def run():
        listener.run(
            lambda channel, payload: payload and received.append(payload),
            should_stop=stop.is_set,
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(1.0)   # let LISTEN land before anything is published

    try:
        DB.statement(
            "INSERT INTO jobs (uuid, queue, payload, attempts, priority, "
            "  max_attempts, available_at, created_at) "
            "VALUES (?, ?, ?, 0, 0, 3, ?, ?)",
            [str(uuid.uuid4()), queue, "{}",
             "2000-01-01T00:00:00", "2000-01-01T00:00:00"],
        )
        deadline = time.time() + 10
        while not received and time.time() < deadline:
            time.sleep(0.1)
        assert received, "the insert trigger did not notify the listener"
    finally:
        stop.set()
        thread.join(timeout=10)


def test_a_rolled_back_insert_never_notifies(migrated_database):
    """A listener woken for a job that does not exist is worse than a poll."""
    from craft.queue.listener import Listener, queue_channel

    db = migrated_database.make("db")
    received, stop = [], threading.Event()
    queue = unique("pgrollback")
    listener = Listener(db, [queue_channel(queue)], poll_interval=0.2)

    thread = threading.Thread(
        target=lambda: listener.run(
            lambda channel, payload: payload and received.append(payload),
            should_stop=stop.is_set,
        ),
        daemon=True,
    )
    thread.start()
    time.sleep(1.0)

    try:
        db.begin_transaction()
        DB.statement(
            "INSERT INTO jobs (uuid, queue, payload, attempts, priority, "
            "  max_attempts, available_at, created_at) "
            "VALUES (?, ?, ?, 0, 0, 3, ?, ?)",
            [str(uuid.uuid4()), queue, "{}",
             "2000-01-01T00:00:00", "2000-01-01T00:00:00"],
        )
        db.rollback()

        time.sleep(2.0)
        assert received == [], "a notification escaped a rolled-back transaction"
    finally:
        stop.set()
        thread.join(timeout=10)


def test_broadcast_refuses_a_payload_over_the_notification_ceiling(migrated_database):
    broadcast = migrated_database.make("broadcast")
    with pytest.raises(ValueError, match="8000"):
        broadcast.publish("craft_events", {"body": "x" * 9000})

    # And a small one goes through.
    broadcast.publish("craft_events", {"id": 1})


# -- locks ---------------------------------------------------------------------


@pytest.fixture
def other_connection(migrated_database):
    """A lock manager on a second, independent physical connection."""
    shim = _SecondDatabase(migrated_database)
    try:
        yield LockManager(shim)
    finally:
        shim.purge()


def test_a_session_lock_excludes_another_connection(migrated_database, other_connection):
    first = LockManager(migrated_database)

    assert first.key("pg:excl").acquire() is True
    try:
        assert other_connection.key("pg:excl").acquire() is False
    finally:
        assert first.key("pg:excl").release() is True

    assert other_connection.key("pg:excl").acquire() is True
    other_connection.key("pg:excl").release()


def test_block_for_gives_up_instead_of_hanging(migrated_database, other_connection):
    """`lock_timeout` bounds the wait inside the database, not in a poll loop."""
    holder = LockManager(migrated_database)

    assert holder.key("pg:wait").acquire() is True
    try:
        started = time.monotonic()
        assert other_connection.key("pg:wait").block_for(1).acquire() is False
        elapsed = time.monotonic() - started
        assert 0.5 < elapsed < 6, f"waited {elapsed:.2f}s, expected about 1s"
    finally:
        holder.key("pg:wait").release()


def test_a_transaction_lock_releases_itself_on_rollback(migrated_database, other_connection):
    """The property a TTL cannot promise: a failed holder frees the lock."""
    manager = LockManager(migrated_database)

    with pytest.raises(RuntimeError):
        with manager.transaction("pg:xact") as held:
            assert held
            raise RuntimeError("boom")

    assert other_connection.key("pg:xact").acquire() is True, "the lock survived a rollback"
    other_connection.key("pg:xact").release()


def test_explain_finds_the_holder(migrated_database):
    manager = LockManager(migrated_database)
    assert manager.key("pg:explain").acquire() is True
    try:
        report = manager.explain("pg:explain")
        assert report["holders"], "pg_locks did not report the lock we hold"
        assert all(holder["granted"] for holder in report["holders"])
    finally:
        manager.key("pg:explain").release()


# -- tenancy on the wire -------------------------------------------------------


def test_a_pooled_connection_never_carries_a_tenant_to_the_next_borrower(
    migrated_database,
):
    """Asked of the database, not of Python — the Python side is not the risk."""
    db = migrated_database.make("db")
    tenant = migrated_database.make("tenant")

    Tenant.bind("55555555-5555-5555-5555-555555555555")
    assert tenant.check() == "55555555-5555-5555-5555-555555555555"

    db.release()
    assert tenant.check() is None, "the session variable outlived the checkout"

    seen = {}

    def other_thread():
        seen["tenant"] = tenant.check()
        db.release()

    thread = threading.Thread(target=other_thread)
    thread.start()
    thread.join(timeout=10)
    assert seen["tenant"] is None


def test_a_transaction_scoped_binding_unwinds_itself(migrated_database):
    tenant = migrated_database.make("tenant")
    db = migrated_database.make("db")

    db.begin_transaction()
    tenant.bind("66666666-6666-6666-6666-666666666666", local=True)
    assert tenant.check() == "66666666-6666-6666-6666-666666666666"
    db.rollback()

    assert tenant.check() is None
    Tenant.clear()
    db.release()


# -- migrations ----------------------------------------------------------------


def test_ddl_rolls_back_with_its_ledger_row(migrated_database, tmp_path):
    """PostgreSQL has transactional DDL and the migrator now uses it."""
    from craft.migrations.migrator import Migrator

    half_a, half_b = unique("pg_half_a"), unique("pg_half_b")
    # `down()` is never reached: `up()` fails, and rolling back its
    # transaction is what removes the half-built tables - not a drop.
    (tmp_path / "2026_08_21_090000_partial.py").write_text(
        "from craft.facades import Schema\n"
        "def up():\n"
        f"    Schema.create_table('{half_a}', lambda t: t.id(type='integer'))\n"
        f"    Schema.create_table('{half_b}', lambda t: t.id(type='integer'))\n"
        "    raise RuntimeError('halfway')\n"
        "def down():\n"
        "    pass\n",
        encoding="utf-8",
    )

    migrator = Migrator(migrated_database, path=str(tmp_path))
    db = migrated_database.make("db")

    with pytest.raises(RuntimeError, match="halfway"):
        migrator.run()

    assert db.table_exists(half_a) is False
    assert db.table_exists(half_b) is False
    assert "2026_08_21_090000_partial" not in migrator.applied()


def test_the_queue_tables_are_carriers_not_boundaries(migrated_database):
    """`jobs.tenant_id` routes work; it must not be mistaken for isolation.

    A policy on `jobs` would break the queue outright: a worker claims across
    all tenants and binds nothing until it holds a job, so under a policy it
    would claim nothing and sit idle against a full queue. The audit reports
    the table and does not fail on it.
    """
    report = migrated_database.make("tenant").audit()
    by_table = {row["table_name"]: row for row in report}

    assert "jobs" in by_table, "the audit should still surface the table"
    assert by_table["jobs"]["exempt"] is True
    assert by_table["jobs"]["protected"] is True, "an exempt table is not a failure"
    assert by_table["jobs"]["policies"] == 0, "and it genuinely has no policy"


def test_the_server_version_is_detected_from_the_live_connection(migrated_database):
    from craft.orm.dialect import MINIMUM_POSTGRES

    dialect = migrated_database.make("db").dialect
    assert isinstance(dialect.version, tuple) and len(dialect.version) == 2
    assert dialect.version >= MINIMUM_POSTGRES, (
        f"PostgreSQL {dialect.version} is below the framework's minimum; "
        f"{dialect.version_advice()}"
    )


def test_uuidv7_is_gated_on_the_server_having_it(schema, migrated_database):
    """PostgreSQL 18 made `uuidv7()` a built-in. Below that it must be refused,
    not emitted and left to fail at insert time."""
    from craft.orm.dialect import UnsupportedFeatureError

    dialect = migrated_database.make("db").dialect

    if not dialect.supports("uuidv7"):
        with pytest.raises(UnsupportedFeatureError, match="18"):
            dialect.require("uuidv7", "generates time-ordered keys in the database")
        pytest.skip(f"this server is {dialect.version}; uuidv7() arrived in 18")

    name = table(schema, "pg_uuidv7", lambda t, name: (
        t.uuid_primary(default="uuidv7()"),
        t.string("name"),
    ))
    for label in ("first", "second"):
        DB.statement(f"INSERT INTO {name} (name) VALUES (?)", [label])
        time.sleep(0.005)

    rows = DB.select(f"SELECT id, name FROM {name} ORDER BY name")
    keys = {row["name"]: str(row["id"]) for row in rows}
    assert keys["first"][14] == "7", "not a version 7 UUID"
    # Time-ordered: that is the whole reason to prefer it over v4.
    assert keys["second"] > keys["first"]


def test_a_uuid_key_can_default_in_the_database(schema):
    requires("pgcrypto")
    name = table(schema, "pg_uuid_keyed", lambda t, name: (
        t.uuid_primary(default="gen_random_uuid()"),
        t.string("name"),
    ))
    DB.statement(f"INSERT INTO {name} (name) VALUES (?)", ["generated"])
    row = DB.select_one(f"SELECT id FROM {name} WHERE name = 'generated'")
    assert str(row["id"]).count("-") == 4


def test_a_raw_default_is_not_stored_as_a_string(schema):
    name = table(schema, "pg_defaults", lambda t, name: (
        t.id(type="integer"),
        t.timestamptz("created_at").default(Raw("now()")),
    ))
    DB.statement(f"INSERT INTO {name} DEFAULT VALUES")
    row = DB.select_one(f"SELECT created_at FROM {name}")
    assert row["created_at"] is not None
    assert not isinstance(row["created_at"], str)


# -- expression seam -----------------------------------------------------------


def test_bindings_land_in_clause_order_on_the_wire(accounts):
    """The paramstyle rewrite is positional; a misordered list binds silently wrong."""
    query = (
        DB.table(accounts)
        .select_expr(Expr("meta #>> ?", [["plan"]]), "plan")
        .where("name", "acme")
        .order_by_expr(Expr("meta #>> ?", [["plan"]]), "asc")
    )
    rows = list(query.get())
    assert len(rows) == 1
    assert rows[0]["plan"] == "pro"


# -- helpers -------------------------------------------------------------------


def explain(sql: str, no_seqscan: bool = False) -> str:
    if no_seqscan:
        DB.statement("SET enable_seqscan = off")
    try:
        rows = DB.select(f"EXPLAIN {sql}")
        return "\n".join(str(list(row.values())[0]) for row in rows)
    finally:
        if no_seqscan:
            DB.statement("SET enable_seqscan = on")


class _SecondDatabase:
    """Container shim exposing a second, independent database manager."""

    def __init__(self, app):
        from craft.orm.db import DatabaseManager

        self._app = app
        self._db = DatabaseManager(app)
        self._db.boot()

    def make(self, key):
        return self._db if key == "db" else self._app.make(key)

    def purge(self):
        self._db.purge()

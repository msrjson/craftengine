"""Eager loading — `with_()` must collapse N+1 into a fixed number of queries.

These tests count the SQL actually issued. Asserting on results alone would pass
just as happily with lazy loading, which is the bug being prevented.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.orm.exceptions import RelationNotFoundError
from craft.orm.model import Model


#: Nothing is dropped or deleted between tests (NR-02). The tables carry a
#: suffix of this module's own and are built once; every test seeds its own
#: rows under a `batch` marker and every root query filters on it, so the
#: counts below see exactly the rows the test wrote.
_SUFFIX = uuid.uuid4().hex[:8]
AUTHORS = f"el_authors_{_SUFFIX}"
POSTS = f"el_posts_{_SUFFIX}"
COMMENTS = f"el_comments_{_SUFFIX}"
TAGS = f"el_tags_{_SUFFIX}"
AUTHOR_TAG = f"el_author_tag_{_SUFFIX}"


class Comment(Model):
    __table__ = COMMENTS
    fillable = ["body", "post_id"]

    def post(self):
        return self.belongs_to(Post, foreign_key="post_id")


class Post(Model):
    __table__ = POSTS
    fillable = ["title", "author_id", "batch"]

    def author(self):
        return self.belongs_to(Author, foreign_key="author_id")

    def comments(self):
        return self.has_many(Comment, foreign_key="post_id")


class Author(Model):
    __table__ = AUTHORS
    fillable = ["name", "batch"]

    def posts(self):
        return self.has_many(Post, foreign_key="author_id")

    def latest_post(self):
        return self.has_one(Post, foreign_key="author_id")

    def tags(self):
        return self.belongs_to_many(
            Tag,
            pivot_table=AUTHOR_TAG,
            foreign_pivot_key="author_id",
            related_pivot_key="tag_id",
        )


class Tag(Model):
    __table__ = TAGS
    fillable = ["label"]


class QueryCounter:
    """Wraps the DatabaseManager to count SELECTs issued."""

    def __init__(self, db):
        self.db = db
        self.queries = []
        self._original = db.statement

    def __enter__(self):
        def counting(query, bindings=None, read=False):
            if query.lstrip().upper().startswith("SELECT"):
                self.queries.append(query)
            return self._original(query, bindings, read)

        self.db.statement = counting
        return self

    def __exit__(self, *exc):
        self.db.statement = self._original
        return False

    @property
    def count(self) -> int:
        return len(self.queries)


@pytest.fixture
def counter(migrated_database):
    return lambda: QueryCounter(migrated_database.make("db"))


@pytest.fixture(scope="module", autouse=True)
def tables(migrated_database):
    schema = migrated_database.make("schema")
    schema.create_table(AUTHORS, lambda t: (
        t.id(), t.string("name"), t.string("batch").nullable(), t.timestamps(),
    ))
    schema.create_table(POSTS, lambda t: (
        t.id(), t.string("title"), t.big_integer("author_id").nullable(),
        t.string("batch").nullable(), t.timestamps(),
    ))
    schema.create_table(COMMENTS, lambda t: (
        t.id(), t.string("body"), t.big_integer("post_id").nullable(), t.timestamps(),
    ))
    schema.create_table(TAGS, lambda t: (t.id(), t.string("label"), t.timestamps()))
    schema.create_table(AUTHOR_TAG, lambda t: (
        t.id(), t.big_integer("author_id"), t.big_integer("tag_id"),
    ))


@pytest.fixture
def batch(tables) -> str:
    """Seed three authors, six posts, twelve comments and two tags; return their marker."""
    marker = uuid.uuid4().hex
    authors = [Author.create({"name": f"author-{i}", "batch": marker}) for i in range(3)]
    for author in authors:
        for j in range(2):
            post = Post.create(
                {"title": f"{author.get_attribute('name')}-post-{j}",
                 "author_id": author.get_attribute("id"), "batch": marker}
            )
            Comment.create({"body": "c1", "post_id": post.get_attribute("id")})
            Comment.create({"body": "c2", "post_id": post.get_attribute("id")})

    tag = Tag.create({"label": "python"})
    other = Tag.create({"label": "orm"})
    for author in authors:
        author.tags().attach(tag.get_attribute("id"))
    authors[0].tags().attach(other.get_attribute("id"))
    return marker


def authors_of(marker: str):
    """The root author query, limited to one test's batch."""
    return Author.query().where("batch", marker)


def posts_of(marker: str):
    """The root post query, limited to one test's batch."""
    return Post.query().where("batch", marker)


class TestHasManyEagerLoading:
    def test_lazy_loading_is_n_plus_1(self, counter, batch):
        """Baseline: without with_(), each parent costs a query."""
        with counter() as c:
            authors = authors_of(batch).get()
            for author in authors:
                author.posts().get()
        assert c.count == 4  # 1 for authors + 3 for each author's posts

    def test_eager_loading_is_two_queries(self, counter, batch):
        with counter() as c:
            authors = authors_of(batch).with_("posts").get()
            for author in authors:
                author.posts().get()
        assert c.count == 2  # 1 for authors + 1 for all posts

    def test_eager_loaded_results_are_correct(self, batch):
        authors = authors_of(batch).with_("posts").order_by("id").get()
        for author in authors:
            posts = author.posts().get()
            assert len(posts) == 2
            for post in posts:
                assert post.get_attribute("author_id") == author.get_attribute("id")

    def test_count_uses_the_cache(self, counter, batch):
        with counter() as c:
            authors = authors_of(batch).with_("posts").get()
            totals = [author.posts().count() for author in authors]
        assert totals == [2, 2, 2]
        assert c.count == 2

    def test_relation_loaded_flag(self, batch):
        eager = authors_of(batch).with_("posts").first()
        lazy = authors_of(batch).first()
        assert eager.relation_loaded("posts") is True
        assert lazy.relation_loaded("posts") is False

    def test_parent_without_children_gets_an_empty_collection(self, counter, batch):
        Author.create({"name": "childless", "batch": batch})
        authors = authors_of(batch).with_("posts").get()
        childless = [a for a in authors if a.get_attribute("name") == "childless"][0]
        assert len(childless.posts().get()) == 0

    def test_empty_result_set_issues_no_relation_query(self, counter, batch):
        with counter() as c:
            authors_of(batch).where("name", "nobody").with_("posts").get()
        assert c.count == 1


class TestBelongsToEagerLoading:
    def test_eager_loading_the_parent_is_two_queries(self, counter, batch):
        with counter() as c:
            posts = posts_of(batch).with_("author").get()
            for post in posts:
                post.author().first()
        assert c.count == 2

    def test_belongs_to_resolves_the_right_owner(self, batch):
        posts = posts_of(batch).with_("author").get()
        for post in posts:
            author = post.author().first()
            assert author.get_attribute("id") == post.get_attribute("author_id")

    def test_duplicate_foreign_keys_are_queried_once(self, counter, batch):
        # Six posts share three authors — the IN clause must dedupe.
        with counter() as c:
            posts = posts_of(batch).with_("author").get()
            [p.author().first() for p in posts]
        assert len(posts) == 6
        assert c.count == 2

    def test_null_foreign_key_yields_none(self, batch):
        Post.create({"title": "orphan", "author_id": None, "batch": batch})
        posts = posts_of(batch).with_("author").get()
        orphan = [p for p in posts if p.get_attribute("title") == "orphan"][0]
        assert orphan.author().first() is None


class TestHasOneEagerLoading:
    def test_has_one_loads_a_single_model(self, counter, batch):
        with counter() as c:
            authors = authors_of(batch).with_("latest_post").get()
            singles = [a.latest_post().get() for a in authors]
        assert c.count == 2
        assert all(isinstance(s, Post) for s in singles)


class TestBelongsToManyEagerLoading:
    def test_pivot_relation_is_two_queries(self, counter, batch):
        with counter() as c:
            authors = authors_of(batch).with_("tags").get()
            for author in authors:
                author.tags().get()
        assert c.count == 2

    def test_pivot_rows_land_on_the_right_parent(self, batch):
        authors = authors_of(batch).with_("tags").order_by("id").get()
        counts = [len(a.tags().get()) for a in authors]
        assert counts == [2, 1, 1]

    def test_pivot_alias_is_not_leaked_as_a_real_column(self, batch):
        author = authors_of(batch).with_("tags").order_by("id").first()
        tag = author.tags().get()[0]
        assert tag.get_attribute("label") in ("python", "orm")


class TestMultipleAndInvalidRelations:
    def test_two_relations_cost_one_query_each(self, counter, batch):
        with counter() as c:
            posts = posts_of(batch).with_("author", "comments").get()
            for post in posts:
                post.author().first()
                post.comments().get()
        assert c.count == 3  # posts + authors + comments

    def test_repeated_relation_names_are_deduped(self, counter, batch):
        with counter() as c:
            posts_of(batch).with_("author", "author").get()
        assert c.count == 2

    def test_without_removes_a_queued_relation(self, counter, batch):
        with counter() as c:
            posts_of(batch).with_("author").without("author").get()
        assert c.count == 1

    def test_unknown_relation_raises(self, batch):
        with pytest.raises(RelationNotFoundError):
            authors_of(batch).with_("nonexistent").get()

    def test_lazy_access_still_works_after_eager_loading_another_relation(self, counter, batch):
        with counter() as c:
            posts = posts_of(batch).with_("author").get()
            posts[0].comments().get()
        assert c.count == 3  # posts + authors + one lazy comments query

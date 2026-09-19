"""The documentation library, shared by the app's /docs routes and the static site.

The reason this is one implementation and not two: Markdown links between
guides are written the way they must be to work *on GitHub* — `postgres.md`,
`orm.md#eager-loading` — and neither consumer serves paths shaped like that.
Left alone, every cross-reference is a 404, which is what the application did
before this: `/docs/orm` rendered `href="postgres.md"`, the browser resolved it
to `/docs/postgres.md`, and the route looked for `postgres.md.md`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import re

import pytest
from craft.support.docs import BrokenLink, DocsLibrary
from craft.support.docs_site import DocsSiteBuilder


@pytest.fixture
def docs_dir():
    from bootstrap.app import app

    return os.path.join(app.base_path, "documentation")


@pytest.fixture
def library(docs_dir):
    return DocsLibrary(docs_dir)


# -- discovery -----------------------------------------------------------------


def test_every_guide_is_discovered(library):
    slugs = library.slugs()
    assert "orm" in slugs and "postgres" in slugs
    assert "README" not in slugs and "readme" not in slugs, "the index is not a page"


def test_titles_come_from_the_document_not_the_filename(library):
    assert library.title("postgres") == "PostgreSQL"
    assert library.title("orm").startswith("Craft ORM")


def test_a_new_guide_is_reachable_before_it_is_filed(library):
    """Unfiled pages land under "More" rather than vanishing from the sidebar."""
    headings = [group["heading"] for group in library.navigation()]
    filed = {item["slug"] for group in library.navigation() for item in group["items"]}
    assert filed == set(library.slugs()), "a page disappeared from the navigation"
    assert headings[0] == "Getting started"


# -- link rewriting ------------------------------------------------------------


@pytest.mark.parametrize(
    "style,expected",
    [
        ("app", "/docs/postgres"),
        ("static", "postgres.html"),
    ],
)
def test_a_cross_page_link_is_rewritten_per_consumer(docs_dir, style, expected):
    assert DocsLibrary(docs_dir, link_style=style).rewrite("postgres.md") == expected


@pytest.mark.parametrize(
    "style,expected",
    [
        ("app", "/docs/orm#eager-loading"),
        ("static", "orm.html#eager-loading"),
    ],
)
def test_an_anchor_survives_the_rewrite(docs_dir, style, expected):
    assert DocsLibrary(docs_dir, link_style=style).rewrite("orm.md#eager-loading") == expected


def test_an_absolute_link_is_left_alone(library):
    for href in ("https://example.com/x", "mailto:a@b.c", "#section"):
        assert library.rewrite(href) == href


def test_a_link_escaping_the_docs_directory_goes_to_github(library):
    """`../CHANGELOG.md` exists in the repository but not in the site."""
    rewritten = library.rewrite("../CHANGELOG.md")
    assert rewritten.startswith("https://github.com/")
    assert rewritten.endswith("/CHANGELOG.md")


def test_a_non_markdown_relative_link_is_untouched(library):
    assert library.rewrite("assets/diagram.png") == "assets/diagram.png"


def test_hrefs_inside_code_blocks_are_not_rewritten(tmp_path):
    """The rewrite is a renderer rule, not a regex over finished HTML."""
    (tmp_path / "sample.md").write_text(
        '# Sample\n\nA real link to [the ORM](orm.md).\n\n```html\n<a href="orm.md">left exactly as written</a>\n```\n',
        encoding="utf-8",
    )
    html = DocsLibrary(str(tmp_path), link_style="static").render("sample")

    assert 'href="orm.html"' in html, "the real link was not rewritten"
    assert "&quot;orm.md&quot;" in html or 'href="orm.md"' in html.split("<code")[1], (
        "the sample inside the code block was rewritten"
    )


def test_the_rendered_page_has_no_dangling_markdown_links(library):
    """The bug this whole module exists to close, asserted on real content."""
    html = library.render("orm")
    hrefs = re.findall(r'href="([^"]+)"', html)
    relative_md = [h for h in hrefs if h.endswith(".md") and not h.startswith("http")]
    assert relative_md == [], f"unrewritten links: {relative_md}"


# -- the link checker ----------------------------------------------------------


def test_the_shipped_documentation_has_no_broken_links(library):
    assert library.broken_links() == []


def test_a_broken_link_is_reported(tmp_path):
    (tmp_path / "a.md").write_text("# A\n\nSee [B](b.md).\n", encoding="utf-8")
    problems = DocsLibrary(str(tmp_path)).broken_links()

    assert len(problems) == 1
    assert "a.md -> b.md" in problems[0]


def test_the_build_refuses_to_publish_a_broken_link(tmp_path):
    """Fails the build rather than shipping a 404 — an author never sees these,
    because the file they linked to is open in front of them."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.md").write_text("# A\n\nSee [gone](gone.md).\n", encoding="utf-8")

    builder = DocsSiteBuilder(str(source), str(tmp_path / "out"))
    with pytest.raises(BrokenLink, match="gone"):
        builder.build()

    assert not os.path.isdir(tmp_path / "out"), "a broken site was written anyway"


# -- the static site -----------------------------------------------------------


@pytest.fixture
def built_site(docs_dir, tmp_path):
    out = tmp_path / "site"
    DocsSiteBuilder(docs_dir, str(out)).build()
    return out


def test_every_guide_becomes_a_page(built_site, library):
    for slug in library.slugs():
        assert (built_site / f"{slug}.html").is_file(), f"{slug} was not written"


def test_the_site_has_an_index_and_a_stylesheet(built_site):
    assert (built_site / "index.html").is_file()
    assert (built_site / "assets" / "style.css").is_file()


def test_jekyll_is_disabled(built_site):
    """Without this GitHub Pages runs the output through Jekyll."""
    assert (built_site / ".nojekyll").is_file()


def test_pages_are_self_describing(built_site):
    html = (built_site / "postgres.html").read_text(encoding="utf-8")
    assert "<title>PostgreSQL — Craft Engine</title>" in html
    assert 'href="assets/style.css"' in html
    # The sidebar marks where the reader is.
    assert 'aria-current="page"' in html


def test_the_navigation_links_to_files_that_exist(built_site):
    html = (built_site / "index.html").read_text(encoding="utf-8")
    # Only the sidebar: the page body carries links out to GitHub, which are
    # not files in the site and are not supposed to be.
    sidebar = html.split("<nav>", 1)[1].split("</nav>", 1)[0]

    hrefs = re.findall(r'<a href="([^"#]+)"', sidebar)
    assert len(hrefs) > 10, "the sidebar came out suspiciously empty"
    for href in hrefs:
        assert (built_site / href).is_file(), f"sidebar links to missing {href}"


def test_the_site_carries_the_framework_version(built_site):
    import engine

    html = (built_site / "index.html").read_text(encoding="utf-8")
    assert f"v{engine.__version__}-{engine.__release__}" in html


def test_rebuilding_replaces_rather_than_accumulates(docs_dir, tmp_path):
    out = tmp_path / "site"
    DocsSiteBuilder(docs_dir, str(out)).build()
    stale = out / "removed-guide.html"
    stale.write_text("<p>from a previous build</p>", encoding="utf-8")

    DocsSiteBuilder(docs_dir, str(out)).build()
    assert not stale.exists(), "a page deleted from the source survived the rebuild"


# -- the application's own route -----------------------------------------------


def test_the_controller_and_the_site_share_one_implementation():
    """Two copies is how the published site and the running app drift apart."""
    import inspect

    from app.Http.Controllers.Docs.DocsController import DocsController

    source = inspect.getsource(DocsController)
    assert "DocsLibrary" in source
    assert "MarkdownIt" not in source, "the controller renders Markdown on its own again"


def test_the_app_route_renders_cross_links_it_can_serve(docs_dir):
    """`/docs/orm` used to emit `postgres.md`, which the route read as
    `postgres.md.md` and answered with a 404."""
    html = DocsLibrary(docs_dir, link_style="app").render("orm")
    assert 'href="/docs/postgres"' in html

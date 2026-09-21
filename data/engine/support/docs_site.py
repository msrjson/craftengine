"""Builds the documentation into a directory of static HTML.

For GitHub Pages, which serves files and runs nothing. The Markdown, the
navigation and the link rewriting all come from `craft.support.docs`, the same
code the application's `/docs` routes use — so the published site cannot say
something different from the one you get by running the framework.

Category: Core Framework (Support).
Relations:
  - Driven by `dev.py docs:build`, published by `.github/workflows/deploy.yml`.
References:
  - Guide: `documentation/README.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import html
import os
import re
import shutil
from typing import List

from engine.support.docs import DocsLibrary

#: Deliberately one file, inlined. A documentation site that needs a build
#: pipeline to render a paragraph is a second project to maintain, and this one
#: has to keep working when nobody has touched it for a year.
STYLESHEET = """
:root{--bg:#fbfcfa;--surface:#fff;--ink:#141917;--ink-2:#4a5450;--rule:#dfe4de;
--accent:#0f5c4e;--code-bg:#eef1ed;--sidebar:#f3f5f2}
@media (prefers-color-scheme:dark){:root{--bg:#0e1312;--surface:#151b19;
--ink:#e4eae6;--ink-2:#aab4b0;--rule:#2b3431;--accent:#5bc4a8;--code-bg:#131917;
--sidebar:#111716}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
.layout{display:flex;min-height:100vh;align-items:flex-start}
nav{width:270px;flex:none;background:var(--sidebar);border-right:1px solid var(--rule);
padding:24px 20px;position:sticky;top:0;max-height:100vh;overflow-y:auto}
nav .brand{font-weight:700;font-size:18px;display:block;margin-bottom:20px;
text-decoration:none;color:var(--ink)}
nav h2{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-2);
margin:20px 0 6px}
nav ul{list-style:none;margin:0;padding:0}
nav li{margin:2px 0}
nav a{display:block;padding:4px 8px;border-radius:4px;text-decoration:none;
color:var(--ink-2);font-size:14px}
nav a:hover{background:var(--surface);color:var(--ink)}
nav a[aria-current]{background:var(--accent);color:#fff}
main{flex:1;min-width:0;padding:40px 48px 96px;max-width:60rem}
main h1{margin-top:0;line-height:1.15}
main h2{margin-top:2em;padding-bottom:.25em;border-bottom:1px solid var(--rule)}
code{background:var(--code-bg);padding:.12em .34em;border-radius:3px;font-size:.88em}
pre{background:var(--code-bg);border:1px solid var(--rule);border-radius:4px;
padding:14px 16px;overflow-x:auto}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;display:block;overflow-x:auto}
th,td{border:1px solid var(--rule);padding:8px 10px;text-align:left}
blockquote{margin:1.2em 0;padding:.5em 1em;border-left:3px solid var(--accent);
background:var(--surface);color:var(--ink-2)}
footer{margin-top:64px;padding-top:16px;border-top:1px solid var(--rule);
color:var(--ink-2);font-size:13px}
@media(max-width:800px){.layout{display:block}nav{width:auto;position:static;
max-height:none;border-right:0;border-bottom:1px solid var(--rule)}
main{padding:24px 20px 64px}}
"""

#: The first paragraph of a guide, used as its meta description.
PARAGRAPH = re.compile(r"<p>(.*?)</p>", re.S)
TAG = re.compile(r"<[^>]+>")
#: Search engines truncate a description past roughly this length.
SUMMARY_LIMIT = 155

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — {project}</title>
{meta}
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="layout">
<nav>
<a class="brand" href="index.html">{project}</a>
{navigation}
</nav>
<main>
{content}
<footer>{version} · <a href="{repo}">Source on GitHub</a></footer>
</main>
</div>
</body>
</html>
"""


def summarize(content: str, fallback: str) -> str:
    """Return a meta description built from a page's opening paragraph.

    A guide that describes itself in its first sentence is exactly what a
    search result should show; without this every page shares one description
    and the engine picks a snippet of navigation instead.

    Args:
        content: The rendered HTML of the page.
        fallback: Used when the page opens with something other than prose.

    Returns:
        A single line of plain text, no longer than `SUMMARY_LIMIT`.
    """
    match = PARAGRAPH.search(content)
    text = " ".join(html.unescape(TAG.sub("", match.group(1))).split()) if match else ""
    if not text:
        return fallback
    if len(text) <= SUMMARY_LIMIT:
        return text
    return text[:SUMMARY_LIMIT].rsplit(" ", 1)[0] + "\u2026"


class DocsSiteBuilder:
    """Renders every page, writes the assets, and refuses to ship a dead link."""

    #: Used when a page opens with a table or a code block instead of prose.
    DESCRIPTION = "Documentation for the Craft Engine Python web framework."

    def __init__(self, docs_dir: str, output_dir: str, project: str = "Craft Engine",
                 base_url: str = ""):
        """Configure the build.

        Args:
            docs_dir: The directory holding the Markdown guides.
            output_dir: The directory to write the site into.
            project: The name shown in the sidebar and in social previews.
            base_url: Where the site will be served, e.g.
                `https://craftengine.org/docs/`. Given one, every page gets a
                canonical URL, social metadata and an entry in `sitemap.xml`;
                without one those are omitted, because a canonical URL guessed
                wrong is worse than none.
        """
        self.library = DocsLibrary(docs_dir, link_style="static")
        self.output_dir = output_dir
        self.project = project
        self.base_url = base_url.rstrip("/") + "/" if base_url else ""

    def version_label(self) -> str:
        try:
            import engine

            return f"v{engine.__version__}-{engine.__release__}"
        except Exception:
            return ""

    def navigation_html(self, current: str) -> str:
        parts = []
        for group in self.library.navigation():
            parts.append(f"<h2>{html.escape(group['heading'])}</h2><ul>")
            for item in group["items"]:
                mark = ' aria-current="page"' if item["slug"] == current else ""
                parts.append(
                    f'<li><a href="{item["slug"]}.html"{mark}>'
                    f'{html.escape(item["title"])}</a></li>'
                )
            parts.append("</ul>")
        return "\n".join(parts)

    def build(self) -> List[str]:
        """Write the site. Returns the files written.

        The link check runs *first* and raises, so a broken cross-reference
        fails the build instead of being published — an author never sees it,
        because the file they linked to is open in front of them.
        """
        from engine.support.docs import BrokenLink

        broken = self.library.broken_links()
        if broken:
            raise BrokenLink(
                "Documentation links point at pages that do not exist:\n  "
                + "\n  ".join(broken)
            )

        if os.path.isdir(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(os.path.join(self.output_dir, "assets"), exist_ok=True)

        written = []
        with open(os.path.join(self.output_dir, "assets", "style.css"), "w",
                  encoding="utf-8") as handle:
            handle.write(STYLESHEET.strip())
        written.append("assets/style.css")

        for slug in self.library.slugs():
            written.append(self._write_page(slug, f"{slug}.html"))

        written.append(self._write_index())

        # Tells GitHub Pages not to run the content through Jekyll, which would
        # otherwise drop anything starting with an underscore without a word.
        nojekyll = os.path.join(self.output_dir, ".nojekyll")
        open(nojekyll, "w", encoding="utf-8").close()
        written.append(".nojekyll")

        if self.base_url:
            written.append(self._write_sitemap(list(written)))

        return written

    def _write_index(self) -> str:
        """The landing page: `README.md` if there is one, else the introduction."""
        readme = os.path.join(self.library.directory, "README.md")
        if os.path.isfile(readme):
            with open(readme, "r", encoding="utf-8") as handle:
                content = self.library.markdown().render(handle.read())
            return self._write("index.html", "Documentation", content, current="")

        first = "introduction" if self.library.exists("introduction") else (
            self.library.slugs() or [None]
        )[0]
        if first is None:
            return self._write("index.html", "Documentation",
                               "<p>No documentation yet.</p>", current="")
        return self._write_page(first, "index.html")

    def _write_page(self, slug: str, filename: str) -> str:
        return self._write(
            filename, self.library.title(slug), self.library.render(slug), current=slug
        )

    def page_url(self, filename: str) -> str:
        """Return the public URL of a page, or an empty string without a base URL.

        Args:
            filename: The page's file name inside the site.

        Returns:
            The absolute URL; `index.html` resolves to the directory itself.
        """
        if not self.base_url:
            return ""
        return self.base_url + ("" if filename == "index.html" else filename)

    def head_meta(self, filename: str, title: str, description: str) -> str:
        """Return the head metadata search engines and social clients read.

        Args:
            filename: The page's file name inside the site.
            title: The page title, unescaped.
            description: The page's meta description, unescaped.

        Returns:
            The metadata elements, one per line.
        """
        heading = f"{html.escape(title)} — {html.escape(self.project)}"
        summary = html.escape(description)
        tags = [f'<meta name="description" content="{summary}">']
        url = self.page_url(filename)
        if url:
            tags += [
                f'<link rel="canonical" href="{url}">',
                '<meta property="og:type" content="article">',
                f'<meta property="og:site_name" content="{html.escape(self.project)}">',
                f'<meta property="og:url" content="{url}">',
                f'<meta property="og:title" content="{heading}">',
                f'<meta property="og:description" content="{summary}">',
                '<meta name="twitter:card" content="summary">',
            ]
        return "\n".join(tags)

    def _write_sitemap(self, pages: List[str]) -> str:
        """Write the sitemap listing every page of the site.

        Args:
            pages: The file names written by this build.

        Returns:
            The file name written.
        """
        urls = "".join(
            f"\n    <url><loc>{self.page_url(page)}</loc></url>"
            for page in pages if page.endswith(".html")
        )
        document = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{urls}\n</urlset>\n"
        )
        with open(os.path.join(self.output_dir, "sitemap.xml"), "w", encoding="utf-8") as handle:
            handle.write(document)
        return "sitemap.xml"

    def _write(self, filename: str, title: str, content: str, current: str) -> str:
        page = PAGE.format(
            title=html.escape(title),
            project=html.escape(self.project),
            meta=self.head_meta(filename, title, summarize(content, self.DESCRIPTION)),
            navigation=self.navigation_html(current),
            content=content,
            version=html.escape(self.version_label()),
            repo="https://github.com/msrjson/craftengine",
        )
        with open(os.path.join(self.output_dir, filename), "w", encoding="utf-8") as handle:
            handle.write(page)
        return filename


__all__ = ["DocsSiteBuilder"]

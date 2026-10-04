"""The documentation library: discovery, navigation and rendering.

One implementation, two consumers — the application's `/docs` routes and the
static site published to GitHub Pages. They used to be one consumer and a plan
for the second, which is how the two would have drifted: a link that works on
the site and 404s in the app is exactly the kind of difference nobody notices
until a reader reports it.

Category: Core Framework (Support).
Relations:
  - Used by `app/Http/Controllers/Blog/DocsController.py` and by
    `dev.py docs:build`.
  - Reads the Markdown in `documentation/`.
References:
  - Guide: `documentation/README.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

#: Ordered groups for the sidebar. Anything not listed lands under "More", so a
#: new file is reachable the moment it exists, even before it is filed here.
SECTIONS = [
    ("Getting started", ["introduction", "installation", "configuration", "cli"]),
    ("The essentials", ["container", "routing", "controllers", "views", "validation"]),
    ("Database", ["migrations", "orm", "postgres", "database_safety", "crud-builder"]),
    ("Features", [
        "security", "authorization", "sessions", "cache", "queues_events",
        "resources", "localization", "storage", "mail", "media",
    ]),
    ("AI", ["ai", "agents_mcp", "vector_search"]),
    ("Going further", ["testing", "deployment", "msr", "governance"]),
]

TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

#: Where a link that escapes `documentation/` is sent instead. Those targets
#: (`../CHANGELOG.md`) exist in the repository but not in the published site.
REPO_BLOB_URL = "https://github.com/msrjson/craftengine/blob/master/data"


class BrokenLink(Exception):
    """A documentation page links to something that is not there."""


def github_heading_id(text: str) -> str:
    """The id GitHub gives a heading: lowercase, punctuation dropped, spaces as hyphens.

    Args:
        text: The heading's inline Markdown source.

    Returns:
        The anchor a `guide.md#section` link uses for it.
    """
    kept = "".join(ch for ch in text.strip().lower() if ch.isalnum() or ch in " -_")
    return kept.replace(" ", "-")


class DocsLibrary:
    """Every documentation page, and how to turn one into HTML.

    `link_style` decides how a cross-page `foo.md` is rewritten:

        "app"    -> /docs/foo      (the routes in `routes/web.py`)
        "static" -> foo.html       (a directory of files, as GitHub Pages serves)

    Rewriting is not cosmetic. Markdown links between guides are written the way
    they must be to work *on GitHub* — `postgres.md`, `orm.md#eager-loading` —
    and neither consumer serves paths shaped like that. Left alone, every
    cross-reference in the documentation is a 404.
    """

    def __init__(self, directory: str, link_style: str = "app"):
        if link_style not in ("app", "static"):
            raise ValueError(f"Unknown link style [{link_style}].")
        self.directory = directory
        self.link_style = link_style

    # -- discovery -------------------------------------------------------------

    def slugs(self) -> List[str]:
        if not os.path.isdir(self.directory):
            return []
        return sorted(
            name[:-3]
            for name in os.listdir(self.directory)
            if name.endswith(".md") and name[:-3].lower() != "readme"
        )

    def pages(self) -> Dict[str, str]:
        """Map of slug -> title, the title taken from the document's own H1."""
        found: Dict[str, str] = {}
        for slug in self.slugs():
            found[slug] = self.title(slug)
        return found

    def title(self, slug: str) -> str:
        try:
            with open(self.path(slug), "r", encoding="utf-8") as handle:
                match = TITLE_RE.search(handle.read(4096))
        except OSError:
            match = None
        if match:
            return match.group(1).strip()
        return slug.replace("_", " ").replace("-", " ").title()

    def path(self, slug: str) -> str:
        # `basename` because a slug reaches this from a URL segment.
        return os.path.join(self.directory, f"{os.path.basename(slug)}.md")

    def exists(self, slug: str) -> bool:
        return os.path.isfile(self.path(slug))

    def navigation(self, pages: Optional[Dict[str, str]] = None) -> List[dict]:
        """Group pages for the sidebar, keeping unlisted ones reachable."""
        pages = pages if pages is not None else self.pages()
        grouped: List[dict] = []
        filed = set()

        for heading, slugs in SECTIONS:
            items = [{"slug": s, "title": pages[s]} for s in slugs if s in pages]
            if items:
                grouped.append({"heading": heading, "items": items})
                filed.update(item["slug"] for item in items)

        remaining = [{"slug": s, "title": t} for s, t in pages.items() if s not in filed]
        if remaining:
            grouped.append({"heading": "More", "items": remaining})

        return grouped

    # -- links -----------------------------------------------------------------

    def rewrite(self, href: str) -> str:
        """Turn a Markdown link into one the active consumer can serve."""
        if not href or href.startswith("#"):
            return href
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:      # absolute, leave alone
            return href

        target, anchor = parsed.path, f"#{parsed.fragment}" if parsed.fragment else ""

        if target.startswith("../"):
            # Outside `documentation/`: exists in the repository, not in the
            # published site. Send the reader to the file on GitHub.
            return f"{REPO_BLOB_URL}/{target[3:]}{anchor}"

        if not target.endswith(".md"):
            return href

        slug = os.path.basename(target)[:-3]
        if self.link_style == "static":
            return f"{slug}.html{anchor}"
        return f"/docs/{slug}{anchor}"

    def outbound_links(self, slug: str) -> List[Tuple[str, str]]:
        """`(target, anchor)` for every relative Markdown link on a page."""
        with open(self.path(slug), "r", encoding="utf-8") as handle:
            source = handle.read()

        links = []
        for href in re.findall(r"\]\(([^)\s]+)\)", source):
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or href.startswith("#"):
                continue
            if not parsed.path.endswith(".md") or parsed.path.startswith("../"):
                continue
            links.append((os.path.basename(parsed.path)[:-3], parsed.fragment))
        return links

    def broken_links(self) -> List[str]:
        """Every cross-reference that points at a page which does not exist.

        Run before publishing. A dead link between guides is invisible to the
        author — the file is right there while they write it — and only shows up
        as a 404 for a reader.
        """
        problems = []
        targets = set(self.slugs()) | {"README", "readme"}
        for slug in self.slugs() + (["README"] if self._has_readme() else []):
            for target, _anchor in self.outbound_links(slug):
                if target not in targets:
                    problems.append(f"{slug}.md -> {target}.md (no such page)")
        return problems

    def _has_readme(self) -> bool:
        return os.path.isfile(os.path.join(self.directory, "README.md"))

    # -- rendering -------------------------------------------------------------

    def markdown(self):
        """A parser whose link rule routes every href through `rewrite`.

        Done as a renderer rule rather than a regex over the finished HTML, so a
        `href="..."` inside a fenced code block — of which the guides have
        several — is left exactly as the author wrote it.
        """
        from markdown_it import MarkdownIt

        # The guides are written for GitHub: pipe tables are tables, and
        # `guide.md#section` links need ids on the headings.
        parser = MarkdownIt("commonmark").enable("table")
        library = self

        # `add_render_rule` binds the function to the renderer, so the first
        # parameter is the renderer itself — not the token list.
        def link_open(renderer, tokens, index, options, env):
            token = tokens[index]
            href = token.attrGet("href")
            if href is not None:
                token.attrSet("href", library.rewrite(href))
            return renderer.renderToken(tokens, index, options, env)

        def heading_open(renderer, tokens, index, options, env):
            seen = env.setdefault("heading_ids", {})
            base = github_heading_id(tokens[index + 1].content)
            count = seen.get(base, 0)
            seen[base] = count + 1
            tokens[index].attrSet("id", f"{base}-{count}" if count else base)
            return renderer.renderToken(tokens, index, options, env)

        parser.add_render_rule("link_open", link_open)
        parser.add_render_rule("heading_open", heading_open)
        return parser

    def render(self, slug: str) -> str:
        """The page as HTML, with its links pointing where they can be served."""
        with open(self.path(slug), "r", encoding="utf-8") as handle:
            source = handle.read()
        return self.markdown().render(source)


__all__ = ["BrokenLink", "DocsLibrary", "SECTIONS"]

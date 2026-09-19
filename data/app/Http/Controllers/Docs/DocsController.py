"""DocsController — serves the Markdown documentation as HTML.

Pages are discovered from the `documentation/` directory, so adding a guide is
a matter of dropping a `.md` file in — no navigation to update by hand.

Discovery, navigation and rendering all live in `craft.support.docs`, shared
with the static site published to GitHub Pages. Keeping two copies is how the
two would drift, and a link that works on the site while 404ing here is the
kind of difference nobody notices until a reader reports it.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from craft.exceptions import NotFoundHttpException
from craft.http import Controller, Request
from craft.support import view
from craft.support.docs import DocsLibrary


class DocsController(Controller):
    def library(self) -> DocsLibrary:
        from craft.facades.base import Facade

        return DocsLibrary(
            os.path.join(Facade._app.base_path, "documentation"), link_style="app"
        )

    def index(self, request: Request):
        library = self.library()
        pages = library.pages()
        first = "introduction" if "introduction" in pages else next(iter(pages), None)
        if first is None:
            raise NotFoundHttpException("No documentation has been published yet.")
        return self.show(request, first)

    def show(self, request: Request, page: str):
        page = os.path.basename(page)  # prevent directory traversal
        library = self.library()

        if not library.exists(page):
            raise NotFoundHttpException(f"Documentation page '{page}' not found.")

        pages = library.pages()
        return view("docs.show", {
            "content": library.render(page),
            "current_page": page,
            "page_title": pages.get(page, page),
            "navigation": library.navigation(pages),
        })

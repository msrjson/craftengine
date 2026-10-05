"""HTTP routes of the catalog module."""

from craft.facades import Proxy, View


def show(sku: str) -> str:
    """Render one product through the module's namespaced view."""
    return View.render("catalog::products.show", {"sku": sku, "price_cents": Proxy.call("catalog", "price_cents", sku)})


def register(router: object) -> None:
    """Register the module's routes; the loader tags them with the slug."""
    router.get("/ext-test/catalog/{sku}", show)

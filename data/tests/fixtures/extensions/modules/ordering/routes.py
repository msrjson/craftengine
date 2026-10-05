"""HTTP routes of the ordering module: it reaches the catalog only through the proxy."""

from craft.facades import Proxy


def quote(sku: str, quantity: int) -> dict:
    """Price an order line without importing the catalog module."""
    return {"sku": sku, "total_cents": Proxy.call("catalog", "price_cents", sku) * quantity}


def register(router: object) -> None:
    """Register the module's routes."""
    router.get("/ext-test/ordering/{sku}/{quantity}", quote)

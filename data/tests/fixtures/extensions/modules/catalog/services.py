"""Catalog prices, the service the `catalog` module exposes on the proxy."""


class CatalogService:
    """Look up product prices in minor units."""

    PRICES = {"tea": 1250, "coffee": 1800}

    def __init__(self, app: object) -> None:
        self._events = app.make("events")

    def price_cents(self, sku: str) -> int:
        """Return the price of `sku` after every `catalog.price_cents` filter."""
        if sku not in self.PRICES:
            raise UnknownProductError(sku)
        return int(self._events.apply_filters("catalog.price_cents", self.PRICES[sku], sku))


class UnknownProductError(LookupError):
    """A domain refusal: the extension working, never a failure of it."""

    status_code = 404
    code = "CATALOG_PRODUCT_UNKNOWN"
    message_key = "catalog.error.product_unknown"

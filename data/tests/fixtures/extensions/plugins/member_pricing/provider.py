"""Discount every catalog price by 10 percent through a filter."""


def register(context: object) -> None:
    """Filter the catalog's prices without importing the catalog."""
    context.filter("catalog.price_cents", lambda price_cents, sku: price_cents * 9 // 10)

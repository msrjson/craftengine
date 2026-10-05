"""Wire the catalog module: its service and its proxy exposure."""

from .services import CatalogService


def register(context: object) -> None:
    """Bind the service and expose its price lookup to other modules."""
    context.app.singleton(CatalogService, lambda c: CatalogService(c))
    context.expose("catalog", CatalogService, {"price_cents"})

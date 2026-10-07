"""Brazil document validator — plugin descriptor and registration.

A legacy `PluginManager` plugin: `PluginManager.discover()` reads the `PLUGIN`
dict, and `load_enabled()` calls `register(app)` once the operator enables the
plugin. The service is bound in the application container, so a project reaches
it through the container rather than importing this package directly.
"""

from plugins.brazil_validator.engine import BrazilValidator

PLUGIN = {
    "slug": "brazil_validator",
    "name": "Brazil Document Validator",
    "version": "1.0.0",
    "description": (
        "Stateless CPF, 2026 alphanumeric CNPJ, Inscrição Estadual for the 27 "
        "states, RG, and CEP/CNAE/phone/address normalizers."
    ),
}


def register(app) -> None:
    """Bind the validator into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("brazil_validator", lambda _container: BrazilValidator())


__all__ = ["PLUGIN", "register", "BrazilValidator"]

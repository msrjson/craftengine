"""Brazil Document Validator Plugin — Native Capability Plugin Descriptor."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .engine import BrazilValidator, DocumentValidatorEngine

PLUGIN = {
    "slug": "brazil_validator",
    "name": "Brazil Document Validator Plugin",
    "version": "2.0.0",
    "description": (
        "Stateless Modulo 11/Modulo 9 CPF, 2026 Alphanumeric CNPJ, 27-state Inscrição Estadual, "
        "RG validation, and CEP/Phone normalizers."
    ),
}


def register(app):
    """Bind the BrazilValidator engine into the application IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("plugin.brazil_validator", lambda c: BrazilValidator())


__all__ = ["PLUGIN", "register", "BrazilValidator", "DocumentValidatorEngine"]

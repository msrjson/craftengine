"""Billing Business Module — Native Module Lifecycle Bootstrap."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from .repositories.billing_repository import BillingRepository
from .routes import register_routes
from .services.billing_service import BillingService

MODULE = {
    "slug": "billing",
    "name": "Financial Billing & Bank Slips",
    "version": "1.0.0",
    "description": "Billing domain module for managing customer invoices and bank slip issuance.",
}


def register(app):
    """Register Billing domain services into the IoC container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("module.billing.repository", lambda c: BillingRepository())
        container.singleton(
            "module.billing.service",
            lambda c: BillingService(repository=c.make("module.billing.repository")),
        )


def boot(app):
    """Boot runtime configuration and mount Billing module HTTP routes."""
    router = getattr(app, "router", None)
    if router:
        register_routes(router)

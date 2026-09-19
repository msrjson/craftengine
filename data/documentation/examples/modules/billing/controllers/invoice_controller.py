"""Thin HTTP Controller for Invoices in Billing Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse

from ..schemas.billing_schema import CreateInvoiceData
from ..services.billing_service import BillingService


class InvoiceController(Controller):
    """HTTP transport controller for invoice management (< 100 lines)."""

    def __init__(self, service: BillingService = None):
        self.service = service or BillingService()

    def index(self, request):
        """List customer invoices and render view or JSON response."""
        invoices = self.service.list_invoices()
        if request.expects_json():
            return JsonResponse(invoices)
        return self.view("billing::invoices", {"invoices": invoices})

    def store(self, request):
        """Create a new invoice."""
        data = CreateInvoiceData(
            customer_id=int(request.input("customer_id", 1)),
            total_amount=float(request.input("total_amount", 0.0)),
            items_count=int(request.input("items_count", 1)),
        )
        invoice = self.service.create_invoice(data)
        if request.expects_json():
            return JsonResponse(invoice, status=201)
        return self.view("billing::invoices", {"invoices": self.service.list_invoices()})

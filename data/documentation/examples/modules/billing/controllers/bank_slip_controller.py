"""Thin HTTP Controller for Bank Slips in Billing Module."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import JsonResponse

from ..schemas.billing_schema import CreateBankSlipData
from ..services.billing_service import BillingService


class BankSlipController(Controller):
    """HTTP transport controller for bank slip financial issuance (< 100 lines)."""

    def __init__(self, service: BillingService = None):
        self.service = service or BillingService()

    def index(self, request):
        """List bank slips and render view or JSON response."""
        slips = self.service.list_bank_slips()
        if request.expects_json():
            return JsonResponse(slips)
        return self.view("billing::bank_slips", {"bank_slips": slips})

    def store(self, request):
        """Issue a new bank slip."""
        try:
            data = CreateBankSlipData(
                customer_name=request.input("customer_name", ""),
                customer_document=request.input("customer_document", ""),
                amount=float(request.input("amount", 0.0)),
                due_date=request.input("due_date", "2026-12-31"),
                description=request.input("description", None),
            )
            bank_slip = self.service.issue_bank_slip(data)
            if request.expects_json():
                return JsonResponse(bank_slip, status=201)
            return self.view("billing::bank_slips", {"bank_slips": self.service.list_bank_slips()})
        except ValueError as err:
            return JsonResponse({"error": str(err)}, status=422)

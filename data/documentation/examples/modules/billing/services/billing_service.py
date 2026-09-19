"""Billing Business Domain Service."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, List, Optional

from documentation.examples.plugins.brazil_validator.engine import DocumentValidatorEngine

from ..repositories.billing_repository import BillingRepository
from ..schemas.billing_schema import CreateBankSlipData, CreateInvoiceData


class BillingService:
    """Core domain business service managing financial transactions and bank slips."""

    def __init__(self, repository: Optional[BillingRepository] = None):
        self.repository = repository or BillingRepository()

    def issue_bank_slip(self, data: CreateBankSlipData) -> Dict[str, Any]:
        """Issue a new bank slip after validating the customer document via DocumentValidatorEngine."""
        # Detect document type (CPF 11 digits vs CNPJ 14 digits)
        digits = "".join(filter(str.isdigit, data.customer_document))
        if len(digits) == 14:
            validation = DocumentValidatorEngine.validate_cnpj(data.customer_document)
        else:
            validation = DocumentValidatorEngine.validate_cpf(data.customer_document)

        if not validation.is_valid:
            raise ValueError(f"Invalid customer document: {validation.error_message}")

        barcode = f"34191.{digits[:5]} 00000.000000 0 999900000{int(data.amount * 100):06d}"

        record = {
            "customer_name": data.customer_name,
            "customer_document": validation.formatted_document,
            "amount": data.amount,
            "due_date": data.due_date,
            "barcode": barcode,
            "status": "pending",
        }

        return self.repository.create_bank_slip(record)

    def list_bank_slips(self) -> List[Dict[str, Any]]:
        """Retrieve all issued bank slips."""
        return self.repository.get_bank_slips()

    def create_invoice(self, data: CreateInvoiceData) -> Dict[str, Any]:
        """Create a customer invoice record."""
        record = {
            "customer_id": data.customer_id,
            "total_amount": data.total_amount,
            "items_count": data.items_count,
            "status": "issued",
        }
        return self.repository.create_invoice(record)

    def list_invoices(self) -> List[Dict[str, Any]]:
        """Retrieve all invoices."""
        return self.repository.get_invoices()

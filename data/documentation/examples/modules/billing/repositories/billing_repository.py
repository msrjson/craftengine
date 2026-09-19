"""Billing Data Persistence Repository."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import List, Dict, Any


class BillingRepository:
    """Isolated repository for financial data persistence and queries."""

    def __init__(self):
        self._bank_slips: List[Dict[str, Any]] = []
        self._invoices: List[Dict[str, Any]] = []

    def create_bank_slip(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Store a bank slip record in memory / persistence."""
        record["id"] = len(self._bank_slips) + 1
        self._bank_slips.append(record)
        return record

    def get_bank_slips(self) -> List[Dict[str, Any]]:
        """Fetch issued bank slip records."""
        return list(self._bank_slips)

    def create_invoice(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Store an invoice record."""
        record["id"] = len(self._invoices) + 1
        self._invoices.append(record)
        return record

    def get_invoices(self) -> List[Dict[str, Any]]:
        """Fetch customer invoices."""
        return list(self._invoices)

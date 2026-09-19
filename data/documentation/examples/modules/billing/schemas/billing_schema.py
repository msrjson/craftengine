"""Billing request DTOs and validation schemas."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass
from typing import Optional


@dataclass
class CreateBankSlipData:
    """Data transfer object for financial bank slip issuance."""

    customer_name: str
    customer_document: str
    amount: float
    due_date: str
    description: Optional[str] = None


@dataclass
class CreateInvoiceData:
    """Data transfer object for customer invoice generation."""

    customer_id: int
    total_amount: float
    items_count: int = 1

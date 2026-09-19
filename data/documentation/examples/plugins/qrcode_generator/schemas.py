"""QR Code capability plugin options and result DTOs."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class QRCodeOptions:
    """Configuration options for QR code rendering."""

    box_size: int = 10
    border: int = 2
    fill_color: str = "#000000"
    back_color: str = "#FFFFFF"


@dataclass(frozen=True)
class QRCodeResult:
    """Generated QR Code result data."""

    content: str
    svg_output: str
    metadata: Dict[str, Any] = field(default_factory=dict)

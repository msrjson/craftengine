"""The single outcome shape every check in brazil_validator returns."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from .enums import ErrorCode

KEY_PREFIX = "validation.brazil"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of one validation or normalization call. Immutable and stateless."""

    is_valid: bool
    clean: str = ""
    formatted: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    kind: str = "unknown"
    message_key: str = ""
    params: Mapping[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.is_valid

    @property
    def document_type(self) -> str:
        """Backward compatibility for old DocumentValidationResult callers."""
        return self.kind.upper()

    @property
    def formatted_document(self) -> str:
        """Backward compatibility for old DocumentValidationResult callers."""
        return self.formatted or ""

    @property
    def raw_digits(self) -> str:
        """Backward compatibility for old DocumentValidationResult callers."""
        return self.clean

    @property
    def error_message(self) -> Optional[str]:
        """Backward compatibility for old DocumentValidationResult callers."""
        return self.error

    def message(self, locale: Optional[str] = None) -> str:
        """Render message_key for the active locale."""
        if not self.message_key:
            return self.error or ""
        try:
            from engine.support.translation import __

            return __(self.message_key, locale=locale, **dict(self.params))
        except Exception:
            return FALLBACK_MESSAGES.get(self.message_key, self.error or self.message_key)


# Backward compatibility alias
DocumentValidationResult = ValidationResult
DocumentResult = ValidationResult


def ok(kind: str, clean: str, formatted: str, version: str = "") -> ValidationResult:
    return ValidationResult(
        is_valid=True,
        clean=clean,
        formatted=formatted,
        version=version if version else None,
        error=None,
        error_code=None,
        kind=kind,
    )


def fail(kind: str, code: Any, clean: str = "", **params: Any) -> ValidationResult:
    if isinstance(code, ErrorCode):
        code_enum = code
    else:
        code_str = str(code)
        try:
            code_enum = ErrorCode(code_str)
        except ValueError:
            code_enum = ErrorCode.UNKNOWN_ERROR

    msg_key = f"{KEY_PREFIX}.{kind}.{code_enum.value.lower()}"
    error_msg = FALLBACK_MESSAGES.get(msg_key, code_enum.value)

    return ValidationResult(
        is_valid=False,
        clean=clean,
        formatted=None,
        version=None,
        error=error_msg,
        error_code=code_enum,
        kind=kind,
        message_key=msg_key,
        params=dict(params),
    )


FALLBACK_MESSAGES: Dict[str, str] = {
    f"{KEY_PREFIX}.cpf.empty_value": "Enter the CPF.",
    f"{KEY_PREFIX}.cpf.invalid_length": "The CPF must have 11 digits; {actual} were entered.",
    f"{KEY_PREFIX}.cpf.invalid_format": "The CPF accepts digits only.",
    f"{KEY_PREFIX}.cpf.repeated_digits": "This CPF repeats the same digit and does not exist.",
    f"{KEY_PREFIX}.cpf.invalid_checksum": "This CPF check digit is invalid and does not exist at the Receita Federal.",
    f"{KEY_PREFIX}.cnpj.empty_value": "Enter the CNPJ.",
    f"{KEY_PREFIX}.cnpj.invalid_length": "The CNPJ must have 14 characters; {actual} were entered.",
    f"{KEY_PREFIX}.cnpj.invalid_format": (
        "The CNPJ accepts letters and digits in the first 12 characters, and only digits in the last two."
    ),
    f"{KEY_PREFIX}.cnpj.repeated_digits": "This CNPJ repeats the same character and does not exist.",
    f"{KEY_PREFIX}.cnpj.invalid_checksum": "This CNPJ fails the check digit and does not exist at the Receita Federal.",
    f"{KEY_PREFIX}.document.empty_value": "Enter the CPF or the CNPJ.",
    f"{KEY_PREFIX}.document.unknown_version": (
        "A document has 11 characters for a CPF or 14 for a CNPJ; {actual} were entered."
    ),
    f"{KEY_PREFIX}.document.unknown_error": "The document could not be checked.",
    f"{KEY_PREFIX}.ie.empty_value": "Enter the state registration.",
    f"{KEY_PREFIX}.ie.invalid_length": (
        "The state registration of {uf} must have {expected} characters; {actual} were entered."
    ),
    f"{KEY_PREFIX}.ie.invalid_format": "This state registration does not follow the {uf} layout.",
    f"{KEY_PREFIX}.ie.repeated_digits": "This state registration repeats the same character and does not exist.",
    f"{KEY_PREFIX}.ie.invalid_checksum": "This state registration fails the {uf} check digit.",
    f"{KEY_PREFIX}.ie.unsupported_state": (
        "{uf} is not a Brazilian state, and the state registration cannot be checked without one."
    ),
    f"{KEY_PREFIX}.ie.exempt": "Exempt",
    f"{KEY_PREFIX}.rg.empty_value": "Enter the RG.",
    f"{KEY_PREFIX}.rg.invalid_length": "The RG must have between 7 and 9 characters; {actual} were entered.",
    f"{KEY_PREFIX}.rg.invalid_format": "The RG accepts digits and, as the last character, the letter X.",
    f"{KEY_PREFIX}.cep.empty_value": "Enter the postal code.",
    f"{KEY_PREFIX}.cep.invalid_length": "The postal code must have 8 digits; {actual} were entered.",
    f"{KEY_PREFIX}.cep.invalid_format": "The postal code accepts digits only.",
    f"{KEY_PREFIX}.phone.empty_value": "Enter the phone number.",
    f"{KEY_PREFIX}.phone.invalid_length": (
        "The phone number must have 10 digits for a landline or 11 for a mobile; {actual} were entered."
    ),
    f"{KEY_PREFIX}.phone.invalid_format": "This phone number does not have a valid Brazilian area code.",
}

__all__ = [
    "ValidationResult",
    "DocumentValidationResult",
    "DocumentResult",
    "ok",
    "fail",
    "FALLBACK_MESSAGES",
]

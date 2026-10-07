"""BrazilValidator — the plugin's public, stateless service.

One entry point over the document validators and the normalizers. Every method
is a pure function of its arguments: no state, no I/O, safe to call from a
validator rule, a FormRequest, a controller or a batch job.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .documents import (
    mask_cpf,
    mask_cnpj,
    only_alnum,
    only_digits,
    validate_cnpj,
    validate_cpf,
    validate_rg,
)
from .errors import ErrorCode
from .ie import validate_ie
from .normalizers import (
    normalize_address,
    normalize_cep,
    normalize_cnae,
    normalize_cnae_list,
    normalize_phone,
)
from .schemas import ValidationResult, fail

_CPF_LENGTH = 11
_CNPJ_LENGTH = 14


class BrazilValidator:
    """Validation, formatting and normalization of Brazilian identity documents."""

    # -- cleaning and masking ------------------------------------------------

    @staticmethod
    def clean(value: Any, alphanumeric: bool = False) -> str:
        """Canonical storage form: unmasked, and uppercased for a CNPJ."""
        return only_alnum(value) if alphanumeric else only_digits(value)

    @staticmethod
    def format_document(value: Any) -> str:
        """Mask a stored CPF or CNPJ for display, without validating it."""
        chars = only_alnum(value)
        if len(chars) == _CNPJ_LENGTH:
            return mask_cnpj(chars)
        if len(chars) == _CPF_LENGTH and chars.isdigit():
            return mask_cpf(chars)
        return str(value or "").strip()

    @staticmethod
    def mask_privacy_document(value: Any) -> str:
        """Mask a document for screen privacy, keeping only shape hints."""
        chars = only_alnum(value)
        if not chars:
            return "—"
        if len(chars) == _CPF_LENGTH and chars.isdigit():
            return f"***.{chars[3:6]}.{chars[6:9]}-**"
        if len(chars) == _CNPJ_LENGTH:
            return f"**.***.{chars[5:8]}/{chars[8:12]}-**"
        if len(chars) > 4:
            return "*" * (len(chars) - 4) + chars[-4:]
        return "*" * len(chars)

    # -- validators ----------------------------------------------------------

    @staticmethod
    def validate_cpf(value: Any) -> ValidationResult:
        """Validate an 11-digit CPF."""
        return validate_cpf(value)

    @staticmethod
    def validate_cnpj(value: Any) -> ValidationResult:
        """Validate a 14-character CNPJ (legacy numeric or 2026 alphanumeric)."""
        return validate_cnpj(value)

    @staticmethod
    def validate_document(value: Any) -> ValidationResult:
        """Route to CPF or CNPJ by the character length of the input."""
        raw = str(value or "").strip()
        if not raw:
            return fail("document", ErrorCode.EMPTY_VALUE)

        chars = only_alnum(raw)
        if len(chars) == _CPF_LENGTH:
            return validate_cpf(chars)
        if len(chars) == _CNPJ_LENGTH:
            return validate_cnpj(chars)
        return fail("document", ErrorCode.UNKNOWN_VERSION, clean=chars, actual=len(chars))

    @staticmethod
    def validate_rg(value: Any) -> ValidationResult:
        """Validate the shape of an RG (7-9 characters, optional trailing X)."""
        return validate_rg(value)

    @staticmethod
    def validate_ie(value: Any, uf: Any) -> ValidationResult:
        """Validate an Inscrição Estadual for any of the 27 states."""
        return validate_ie(value, uf)

    # -- normalizers ---------------------------------------------------------

    @staticmethod
    def normalize_cep(value: Any) -> ValidationResult:
        """Normalize an eight-digit postal code."""
        return normalize_cep(value)

    @staticmethod
    def normalize_phone(value: Any, country_code: bool = True) -> ValidationResult:
        """Normalize a landline or mobile phone number."""
        return normalize_phone(value, country_code=country_code)

    @staticmethod
    def normalize_cnae(value: Any) -> ValidationResult:
        """Normalize an economic activity code."""
        return normalize_cnae(value)

    @staticmethod
    def normalize_cnae_list(value: Any) -> List[str]:
        """Normalize a list of economic activity codes."""
        return normalize_cnae_list(value)

    @staticmethod
    def normalize_address(payload: Mapping[str, Any]) -> Dict[str, str]:
        """Normalize an address field dictionary."""
        return normalize_address(payload)

    # -- batch ---------------------------------------------------------------

    @staticmethod
    def validate_batch(rows: List[Dict[str, Any]], field: str = "cpf") -> Dict[str, Any]:
        """Split rows into accepted and rejected by the `field` document."""
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for line, row in enumerate(rows or [], start=1):
            provided = row.get(field, "")
            result = BrazilValidator.validate_document(provided)
            if result.is_valid:
                row[field] = result.clean
                row["_document_kind"] = result.kind
                row["_document_version"] = result.version
                accepted.append(row)
            else:
                rejected.append({
                    "line": line,
                    "record": row,
                    "provided_document": provided,
                    "error_code": result.error_code.value if result.error_code else None,
                    "message_key": result.message_key,
                    "params": dict(result.params),
                })

        return {
            "total_processed": len(rows or []),
            "total_accepted": len(accepted),
            "total_rejected": len(rejected),
            "accepted": accepted,
            "rejected": rejected,
        }


__all__ = ["BrazilValidator"]

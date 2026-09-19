"""The main entry point class for Craft Engine's BrazilValidator plugin."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict, List, Mapping

from .enums import ErrorCode
from .normalizers.address import normalize_address
from .normalizers.cep import normalize_cep
from .normalizers.cnae import normalize_cnae, normalize_cnae_list
from .normalizers.phone import normalize_phone
from .schemas import DocumentValidationResult, ValidationResult, fail
from .validators.cnpj import mask_cnpj, validate_cnpj
from .validators.cpf import mask_cpf, only_alnum, only_digits, validate_cpf
from .validators.ie import validate_ie
from .validators.rg import validate_rg


class BrazilValidator:
    """Brazilian personal and company identity document validation and normalization.

    Stateless, pure-function implementation for Craft Engine framework.
    """

    # -- Cleaning & Formatting -----------------------------------------------

    @staticmethod
    def clean(value: Any, alphanumeric: bool = False) -> str:
        """Canonical storage form: unmasked and, for CNPJ, uppercase."""
        if alphanumeric:
            return only_alnum(value)
        return only_digits(value)

    @staticmethod
    def format_document(value: Any) -> str:
        """Mask a stored CPF or CNPJ for display, without validating it."""
        chars = only_alnum(value)
        if len(chars) == 14:
            return mask_cnpj(chars)
        if len(chars) == 11 and chars.isdigit():
            return mask_cpf(chars)
        return str(value or "").strip()

    @staticmethod
    def mask_privacy_document(value: Any) -> str:
        """Mask CPF/CNPJ document digits for workplace screen privacy."""
        chars = only_alnum(value)
        if not chars:
            return "—"
        if len(chars) == 11 and chars.isdigit():
            return f"***.{chars[3:6]}.{chars[6:9]}-**"
        if len(chars) == 14:
            return f"**.***.{chars[5:8]}/{chars[8:12]}-**"
        if len(chars) > 4:
            return "*" * (len(chars) - 4) + chars[-4:]
        return "*" * len(chars)

    # -- Validators ----------------------------------------------------------

    @staticmethod
    def validate_cpf(value: Any) -> ValidationResult:
        """Validate an 11-digit CPF using standard Modulo 11 arithmetic."""
        return validate_cpf(value)

    @staticmethod
    def validate_cnpj(value: Any) -> ValidationResult:
        """Validate a 14-character CNPJ (numeric or 2026 alphanumeric)."""
        return validate_cnpj(value)

    @staticmethod
    def validate_document(value: Any) -> ValidationResult:
        """Route to CPF or CNPJ based on character length."""
        raw = str(value or "").strip()
        if not raw:
            return fail("document", ErrorCode.EMPTY_VALUE)

        chars = only_alnum(raw)
        if len(chars) == 11:
            return validate_cpf(chars)
        if len(chars) == 14:
            return validate_cnpj(chars)

        return fail("document", ErrorCode.UNKNOWN_VERSION, clean=chars, actual=len(chars))

    @staticmethod
    def validate_rg(value: Any) -> ValidationResult:
        """Validate standard RG format (7-9 chars, optional trailing X)."""
        return validate_rg(value)

    @staticmethod
    def validate_ie(value: Any, uf: Any) -> ValidationResult:
        """Validate State Registration (Inscrição Estadual) for any of 27 UFs."""
        return validate_ie(value, uf)

    # -- Normalizers ---------------------------------------------------------

    @staticmethod
    def normalize_cep(value: Any) -> ValidationResult:
        """Normalize 8-digit postal code."""
        return normalize_cep(value)

    @staticmethod
    def normalize_cnae(value: Any) -> ValidationResult:
        """Normalize economic activity code."""
        return normalize_cnae(value)

    @staticmethod
    def normalize_cnae_list(value: Any) -> List[str]:
        """Normalize list of economic activity codes."""
        return normalize_cnae_list(value)

    @staticmethod
    def normalize_phone(value: Any, country_code: bool = True) -> ValidationResult:
        """Normalize landline or mobile phone number."""
        return normalize_phone(value, country_code=country_code)

    @staticmethod
    def normalize_address(payload: Mapping[str, Any]) -> Dict[str, str]:
        """Normalize address field dictionary."""
        return normalize_address(payload)

    # -- Batch Processing ----------------------------------------------------

    @staticmethod
    def validate_batch(rows: List[Dict[str, Any]], field: str = "cpf") -> Dict[str, Any]:
        """Split a dataset batch into accepted and rejected records with diagnostic details."""
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
                rejected.append(
                    {
                        "line": line,
                        "record": row,
                        "provided_document": provided,
                        "error_code": result.error_code,
                        "message_key": result.message_key,
                        "params": dict(result.params),
                    }
                )

        return {
            "total_processed": len(rows or []),
            "total_accepted": len(accepted),
            "total_rejected": len(rejected),
            "accepted": accepted,
            "rejected": rejected,
        }


# Backwards compatibility alias
DocumentValidatorEngine = BrazilValidator

__all__ = ["BrazilValidator", "DocumentValidatorEngine", "DocumentValidationResult"]

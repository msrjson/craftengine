"""Brazilian document validation, formatting and normalization.

The public surface is `BrazilValidator` (`engine.py`): CPF, alphanumeric CNPJ,
Inscrição Estadual for the 27 states, RG, plus CEP, phone, CNAE and address
normalizers. Every check returns a `ValidationResult` carrying a stable
`error_code` and a `message_key`, never a hardcoded sentence.
"""

from plugins.brazil_validator.engine import BrazilValidator

__all__ = ["BrazilValidator"]

"""Unit tests for the upgraded Brazil Validator plugin."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from documentation.examples.plugins.brazil_validator.engine import BrazilValidator, DocumentValidatorEngine


def test_cpf_validation():
    """Verify valid and invalid CPF cases."""
    # Classic valid CPF
    valid_cpf = "11144477735"
    res = BrazilValidator.validate_cpf(valid_cpf)
    assert res.is_valid is True
    assert res.formatted == "111.444.777-35"
    assert res.clean == valid_cpf
    # Backwards compatibility attributes
    assert res.document_type == "CPF"
    assert res.formatted_document == "111.444.777-35"
    assert res.raw_digits == valid_cpf

    # Invalid repeated digits
    res_invalid = BrazilValidator.validate_cpf("11111111111")
    assert res_invalid.is_valid is False
    assert res_invalid.error_code == "REPEATED_DIGITS"

    # Invalid checksum
    res_bad_checksum = BrazilValidator.validate_cpf("11144477730")
    assert res_bad_checksum.is_valid is False
    assert res_bad_checksum.error_code == "INVALID_CHECKSUM"


def test_cnpj_legacy_and_alphanumeric_validation():
    """Verify legacy numeric and 2026 Receita Federal alphanumeric CNPJ formats."""
    # Valid legacy numeric CNPJ: Banco do Brasil (00.000.000/0001-91)
    res_num = BrazilValidator.validate_cnpj("00000000000191")
    assert res_num.is_valid is True
    assert res_num.version == "numeric"
    assert res_num.formatted == "00.000.000/0001-91"

    # Valid 2026 Alphanumeric CNPJ: 12ABC34501DE35
    res_alpha = BrazilValidator.validate_cnpj("12ABC34501DE35")
    assert res_alpha.is_valid is True
    assert res_alpha.version == "alphanumeric"
    assert res_alpha.formatted == "12.ABC.345/01DE-35"

    # Invalid alphanumeric CNPJ
    res_bad_alpha = BrazilValidator.validate_cnpj("12ABC34501DE00")
    assert res_bad_alpha.is_valid is False
    assert res_bad_alpha.error_code == "INVALID_CHECKSUM"


def test_inscricao_estadual_validation_multi_state():
    """Verify State Registration (IE) validation across multiple Brazilian states."""
    # SP valid: 110.042.490.114
    res_sp = BrazilValidator.validate_ie("110042490114", "SP")
    assert res_sp.is_valid is True

    # RJ valid: 99.999.99-3
    res_rj = BrazilValidator.validate_ie("99999993", "RJ")
    assert res_rj.is_valid is True

    # MG valid: 062.307.904/0081
    res_mg = BrazilValidator.validate_ie("0623079040081", "MG")
    assert res_mg.is_valid is True

    # RS valid: 224/0266970
    res_rs = BrazilValidator.validate_ie("2240266970", "RS")
    assert res_rs.is_valid is True

    # Exempt registration
    res_exempt = BrazilValidator.validate_ie("ISENTO", "SP")
    assert res_exempt.is_valid is True
    assert res_exempt.clean == "ISENTO"

    # Unsupported state
    res_bad_uf = BrazilValidator.validate_ie("123456", "XX")
    assert res_bad_uf.is_valid is False
    assert res_bad_uf.error_code == "UNSUPPORTED_STATE"


VALID_IE_VECTORS = {
    "AC": "01.004.823/001-12",
    "AL": "24000004-8",
    "AM": "04.145.871-0",
    "AP": "030123459",
    "BA": "123456-63",
    "CE": "06000001-5",
    "DF": "07300001001-09",
    "ES": "082560722",
    "GO": "10.987.654-7",
    "MA": "12000038-5",
    "MG": "062.307.904/0081",
    "MS": "280215789",
    "MT": "0013000001-9",
    "PA": "15-999999-5",
    "PB": "06000001-5",
    "PE": "0321418-40",
    "PI": "01234567-9",
    "PR": "123.45678-50",
    "RJ": "99.999.99-3",
    "RN": "20.040.040-1",
    "RO": "0000000062521-3",
    "RR": "24006628-1",
    "RS": "224/0266970",
    "SC": "251.040.852",
    "SE": "27123456-3",
    "SP": "110.042.490.114",
    "TO": "29010227836",
}


def test_all_27_states_ie_valid():
    """Verify official SINTEGRA test vectors across all 27 Brazilian Federation units."""
    for uf, vector in VALID_IE_VECTORS.items():
        res = BrazilValidator.validate_ie(vector, uf)
        assert res.is_valid is True, f"Failed for {uf}: {res.error_code}"


def test_cep_and_phone_normalizers():
    """Verify CEP and phone normalization."""
    # CEP
    res_cep = BrazilValidator.normalize_cep("01310-100")
    assert res_cep.is_valid is True
    assert res_cep.clean == "01310100"
    assert res_cep.formatted == "01310-100"

    # Phone (mobile with country code)
    res_phone = BrazilValidator.normalize_phone("(11) 98765-4321")
    assert res_phone.is_valid is True
    assert res_phone.version == "mobile"
    assert res_phone.clean == "5511987654321"
    assert res_phone.formatted == "(11) 98765-4321"


def test_backward_compatibility_alias():
    """Verify DocumentValidatorEngine alias preserves legacy method calls."""
    engine = DocumentValidatorEngine()
    res = engine.validate_cpf("11144477735")
    assert res.is_valid is True
    assert res.document_type == "CPF"
    assert res.raw_digits == "11144477735"

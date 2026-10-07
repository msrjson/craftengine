"""Tests for the official Brazil validator plugin (`plugins/brazil_validator/`).

The plugin is pure logic: CPF, legacy and 2026-alphanumeric CNPJ, Inscrição
Estadual for the 27 states, RG, and the CEP/CNAE/phone/address normalizers.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from engine.plugins.manager import PluginManager
from plugins.brazil_validator import BrazilValidator
from plugins.brazil_validator.errors import ErrorCode


def _code(result):
    return result.error_code.value if result.error_code else None


class TestCpf:
    def test_a_valid_cpf_passes_and_is_masked(self):
        result = BrazilValidator.validate_cpf("529.982.247-25")
        assert result.is_valid is True
        assert result.clean == "52998224725"
        assert result.formatted == "529.982.247-25"

    def test_a_repeated_sequence_is_rejected(self):
        result = BrazilValidator.validate_cpf("111.111.111-11")
        assert _code(result) == ErrorCode.REPEATED_DIGITS.value

    def test_a_wrong_check_digit_is_rejected(self):
        result = BrazilValidator.validate_cpf("529.982.247-26")
        assert _code(result) == ErrorCode.INVALID_CHECKSUM.value

    def test_a_wrong_length_is_rejected(self):
        result = BrazilValidator.validate_cpf("529.982.247")
        assert _code(result) == ErrorCode.INVALID_LENGTH.value

    def test_letters_are_not_accepted(self):
        result = BrazilValidator.validate_cpf("529.982.247-2A")
        assert _code(result) == ErrorCode.INVALID_FORMAT.value

    def test_an_empty_value_is_rejected(self):
        assert _code(BrazilValidator.validate_cpf("")) == ErrorCode.EMPTY_VALUE.value


class TestCnpj:
    def test_a_numeric_cnpj_passes(self):
        result = BrazilValidator.validate_cnpj("11.222.333/0001-81")
        assert result.is_valid is True
        assert result.version == "numeric"
        assert result.formatted == "11.222.333/0001-81"

    def test_an_alphanumeric_cnpj_passes(self):
        result = BrazilValidator.validate_cnpj("12.ABC.345/01DE-35")
        assert result.is_valid is True
        assert result.clean == "12ABC34501DE35"
        assert result.version == "alphanumeric"

    def test_an_alphanumeric_cnpj_with_a_bad_check_digit_fails(self):
        result = BrazilValidator.validate_cnpj("12.ABC.345/01DE-36")
        assert _code(result) == ErrorCode.INVALID_CHECKSUM.value

    def test_a_letter_in_a_check_digit_is_rejected(self):
        result = BrazilValidator.validate_cnpj("12.ABC.345/01DE-3X")
        assert _code(result) == ErrorCode.INVALID_FORMAT.value

    def test_a_repeated_character_cnpj_is_rejected(self):
        result = BrazilValidator.validate_cnpj("00000000000000")
        assert _code(result) == ErrorCode.REPEATED_DIGITS.value


class TestStateRegistration:
    def test_a_valid_sao_paulo_ie_passes(self):
        result = BrazilValidator.validate_ie("110.042.490.114", "SP")
        assert result.is_valid is True
        assert result.formatted == "110.042.490.114"

    def test_an_ie_with_a_bad_check_digit_is_rejected(self):
        result = BrazilValidator.validate_ie("110.042.490.115", "SP")
        assert _code(result) == ErrorCode.INVALID_CHECKSUM.value

    def test_an_unknown_state_is_refused(self):
        result = BrazilValidator.validate_ie("110042490114", "XX")
        assert _code(result) == ErrorCode.UNSUPPORTED_STATE.value

    def test_the_exempt_token_is_accepted_for_any_state(self):
        result = BrazilValidator.validate_ie("ISENTO", "MG")
        assert result.is_valid is True
        assert result.version == "exempt"

    def test_every_state_has_at_least_one_layout(self):
        from plugins.brazil_validator.ie import STATE_RULES

        assert len(STATE_RULES) == 27
        assert all(STATE_RULES[uf] for uf in STATE_RULES)


class TestRgAndRouting:
    def test_an_rg_of_the_right_shape_passes(self):
        assert BrazilValidator.validate_rg("12.345.678-9").is_valid is True

    def test_a_short_rg_is_rejected(self):
        assert _code(BrazilValidator.validate_rg("123")) == ErrorCode.INVALID_LENGTH.value

    def test_validate_document_routes_eleven_characters_to_cpf(self):
        assert BrazilValidator.validate_document("52998224725").kind == "cpf"

    def test_validate_document_routes_fourteen_characters_to_cnpj(self):
        assert BrazilValidator.validate_document("11222333000181").kind == "cnpj"

    def test_validate_document_rejects_an_unknown_length(self):
        assert _code(BrazilValidator.validate_document("12345")) == ErrorCode.UNKNOWN_VERSION.value


class TestNormalizers:
    def test_cep_is_masked(self):
        result = BrazilValidator.normalize_cep("01310100")
        assert result.is_valid is True and result.formatted == "01310-100"

    def test_a_mobile_phone_is_formatted_with_country_code(self):
        result = BrazilValidator.normalize_phone("(11) 98765-4321")
        assert result.is_valid is True
        assert result.clean == "5511987654321"
        assert result.formatted == "(11) 98765-4321"

    def test_a_landline_without_country_code_is_formatted(self):
        result = BrazilValidator.normalize_phone("1132654321", country_code=False)
        assert result.is_valid is True and result.clean == "1132654321"

    def test_an_invalid_area_code_is_rejected(self):
        assert _code(BrazilValidator.normalize_phone("00987654321")) == ErrorCode.INVALID_FORMAT.value

    def test_a_cnae_list_is_normalized_and_deduplicated(self):
        assert BrazilValidator.normalize_cnae_list("6201500, 6201-5/00; 0000000") == ["6201-5/00", "0000-0/00"]

    def test_an_address_is_normalized(self):
        normalized = BrazilValidator.normalize_address({
            "zip": "01310-100", "street": "avenida paulista", "state": "sp",
        })
        assert normalized["zip"] == "01310-100"
        assert normalized["street"] == "Av. paulista"
        assert normalized["state"] == "SP"


class TestBatchAndMessages:
    def test_validate_batch_splits_accepted_and_rejected(self):
        report = BrazilValidator.validate_batch(
            [{"cpf": "529.982.247-25"}, {"cpf": "111.111.111-11"}], field="cpf"
        )
        assert report["total_processed"] == 2
        assert report["total_accepted"] == 1
        assert report["total_rejected"] == 1
        assert report["rejected"][0]["error_code"] == ErrorCode.REPEATED_DIGITS.value

    def test_a_failure_carries_a_message_key_and_its_params(self):
        result = BrazilValidator.validate_cpf("529.982.247")
        assert result.message_key == "validation.brazil.cpf.invalid_length"
        assert result.params["actual"] == 9


class TestPluginWiring:
    def test_the_plugin_is_discoverable_on_disk(self):
        slugs = {descriptor["slug"] for descriptor in PluginManager().discover(os.getcwd())}
        assert "brazil_validator" in slugs

    def test_register_binds_the_service_in_the_container(self):
        from bootstrap.app import app
        from plugins.brazil_validator.plugin import register

        register(app)
        assert isinstance(app.make("brazil_validator"), BrazilValidator)

"""Interpreter that executes state registration validation against SINTEGRA rules."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from typing import Any, Callable, Dict, Optional, Tuple

from ..enums import ErrorCode
from ..schemas import DocumentResult, ValidationResult, fail, ok
from .ie_rules import (
    ALGORITHM_AMAPA,
    ALGORITHM_AMAZONAS,
    ALGORITHM_BAHIA,
    ALGORITHM_GOIAS,
    ALGORITHM_MINAS,
    ALGORITHM_WEIGHTED,
    BRAZILIAN_STATES,
    EXEMPT_TOKENS,
    OVERFLOW_ONE,
    OVERFLOW_SUBTRACT_TEN,
    RULE_DIRECT,
    RULE_LAST_DIGIT,
    RULE_TIMES_TEN,
    STATE_RULES,
    CheckDigit,
    IeLayout,
)

_ASCII_ZERO = 48
_BAHIA_MODULUS_TEN = frozenset("0123458")


def _clean(value: Any) -> str:
    return "".join(c for c in str(value or "") if c.isalnum()).upper()


def apply_mask(value: str, template: str) -> str:
    """Apply mask template consuming characters at '#'."""
    out, index = [], 0
    for slot in template:
        if slot == "#":
            if index >= len(value):
                break
            out.append(value[index])
            index += 1
        else:
            if index < len(value) and value[index] == slot:
                index += 1
            out.append(slot)
    out.append(value[index:])
    return "".join(out)


def _weighted_sum(value: str, digit: CheckDigit) -> int:
    return sum((ord(value[i]) - _ASCII_ZERO) * w for i, w in zip(digit.source, digit.weights))


def _apply_overflow(dv: int, overflow: str) -> int:
    if dv < 10:
        return dv
    if overflow == OVERFLOW_SUBTRACT_TEN:
        return dv - 10
    if overflow == OVERFLOW_ONE:
        return 1 if dv == 11 else 0
    return 0


def _weighted(value: str, digit: CheckDigit, modulus: Optional[int] = None) -> int:
    total = _weighted_sum(value, digit)
    base = modulus if modulus is not None else digit.modulus

    if digit.rule == RULE_DIRECT:
        return total % base
    if digit.rule == RULE_TIMES_TEN:
        dv = (total * 10) % 11
        return 0 if dv == 10 else dv
    if digit.rule == RULE_LAST_DIGIT:
        return (total % 11) % 10

    return _apply_overflow(base - (total % base), digit.overflow)


def _bahia(value: str, digit: CheckDigit, layout: IeLayout) -> int:
    selector = value[layout.modulus_selector] if layout.modulus_selector >= 0 else ""
    modulus = 10 if selector in _BAHIA_MODULUS_TEN else 11
    return _weighted(value, digit, modulus=modulus)


def _minas(value: str, digit: CheckDigit, layout: IeLayout) -> int:
    if digit.position == 12:
        return _weighted(value, digit)

    expanded = value[:3] + "0" + value[3:11]
    total = 0
    for index, char in enumerate(expanded):
        product = (ord(char) - _ASCII_ZERO) * (1 if index % 2 == 0 else 2)
        total += product // 10 + product % 10
    return (total + 9) // 10 * 10 - total


def _goias(value: str, digit: CheckDigit, _layout: IeLayout) -> int:
    remainder = _weighted_sum(value, digit) % 11
    if remainder == 0:
        return 0
    if remainder == 1:
        return 1 if 10103105 <= int(value[:8]) <= 11094402 else 0
    return 11 - remainder


def _amapa(value: str, digit: CheckDigit, _layout: IeLayout) -> int:
    base = int(value[:8])
    if base <= 3017000:
        offset, overflow = 5, 0
    elif base <= 3019022:
        offset, overflow = 9, 1
    else:
        offset, overflow = 0, 0

    dv = 11 - ((offset + _weighted_sum(value, digit)) % 11)
    if dv == 10:
        return 0
    if dv == 11:
        return overflow
    return dv


def _amazonas(value: str, digit: CheckDigit, _layout: IeLayout) -> int:
    total = _weighted_sum(value, digit)
    if total < 11:
        return 11 - total
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


_ALGORITHMS: Dict[str, Callable[[str, CheckDigit, IeLayout], int]] = {
    ALGORITHM_WEIGHTED: lambda value, digit, _layout: _weighted(value, digit),
    ALGORITHM_BAHIA: _bahia,
    ALGORITHM_MINAS: _minas,
    ALGORITHM_GOIAS: _goias,
    ALGORITHM_AMAPA: _amapa,
    ALGORITHM_AMAZONAS: _amazonas,
}


def _assert_table_is_sound() -> None:
    if len(STATE_RULES) != 27:
        raise ValueError(f"ie_rules_state_count:{len(STATE_RULES)}")
    for uf, layouts in STATE_RULES.items():
        if not layouts:
            raise ValueError(f"ie_rules_no_layout:{uf}")
        for layout in layouts:
            if layout.algorithm not in _ALGORITHMS:
                raise ValueError(f"ie_rules_unknown_algorithm:{uf}:{layout.algorithm}")
            for digit in layout.digits:
                if digit.position >= layout.length:
                    raise ValueError(f"ie_rules_digit_out_of_range:{uf}")
                if digit.weights and len(digit.source) != len(digit.weights):
                    raise ValueError(f"ie_rules_weight_mismatch:{uf}")


_assert_table_is_sound()

_PATTERNS: Dict[str, re.Pattern] = {
    layout.pattern: re.compile(layout.pattern) for layouts in STATE_RULES.values() for layout in layouts
}


def _pick_layout(uf: str, value: str) -> Tuple[Optional[IeLayout], Tuple[int, ...]]:
    lengths = tuple(layout.length for layout in STATE_RULES[uf])
    for layout in STATE_RULES[uf]:
        if layout.length == len(value) and _PATTERNS[layout.pattern].match(value):
            return layout, lengths
    return None, lengths


def validate_ie(value: Any, uf: Any) -> ValidationResult:
    """Validate a Brazilian State Registration against the specified state (UF)."""
    state = str(uf or "").strip().upper()[:2]
    if state not in BRAZILIAN_STATES:
        return fail("ie", ErrorCode.UNSUPPORTED_STATE, uf=state)

    raw = str(value or "").strip()
    if not raw:
        return fail("ie", ErrorCode.EMPTY_VALUE, uf=state)

    clean = _clean(raw)
    if clean in EXEMPT_TOKENS:
        return DocumentResult(
            True,
            kind="ie",
            version="exempt",
            formatted="ISENTO",
            clean="ISENTO",
            params={"uf": state},
        )

    layout, lengths = _pick_layout(state, clean)
    if layout is None:
        if not any(length == len(clean) for length in lengths):
            expected = " / ".join(str(length) for length in lengths)
            return fail(
                "ie",
                ErrorCode.INVALID_LENGTH,
                clean=clean,
                uf=state,
                expected=expected,
                actual=len(clean),
            )
        return fail("ie", ErrorCode.INVALID_FORMAT, clean=clean, uf=state)

    if clean == clean[0] * len(clean):
        return fail("ie", ErrorCode.REPEATED_DIGITS, clean=clean, uf=state)

    compute = _ALGORITHMS[layout.algorithm]
    for order, digit in enumerate(layout.digits, start=1):
        expected = compute(clean, digit, layout)
        if (ord(clean[digit.position]) - _ASCII_ZERO) != expected:
            return fail(
                "ie",
                ErrorCode.INVALID_CHECKSUM,
                clean=clean,
                uf=state,
                position=order,
            )

    return ok("ie", clean, apply_mask(clean, layout.mask))

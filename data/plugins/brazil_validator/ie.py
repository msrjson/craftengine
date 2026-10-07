"""Inscrição Estadual (state registration) validation for the 27 states.

The 27 Federation Units do not share one rule, so the table below describes each
accepted layout per state — its length, its shape, its display mask and the
check digits it carries — and one interpreter executes whichever algorithm the
layout names. The layouts follow the SINTEGRA specification; a state may accept
more than one shape (Bahia, Pernambuco, Rondônia, Rio Grande do Norte, Santa
Catarina, São Paulo and Tocantins do).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .errors import ErrorCode
from .schemas import ValidationResult, fail, ok

OVERFLOW_ZERO = "zero"
OVERFLOW_ONE = "one"
OVERFLOW_SUBTRACT_TEN = "subtract_ten"

RULE_COMPLEMENT = "complement"  # dv = modulus - (sum % modulus)
RULE_DIRECT = "direct"  # dv = sum % modulus
RULE_TIMES_TEN = "times_ten"  # dv = (sum * 10) % 11, 10 -> 0
RULE_LAST_DIGIT = "last_digit"  # dv = (sum % 11) % 10

ALGORITHM_WEIGHTED = "weighted"
ALGORITHM_BAHIA = "bahia"
ALGORITHM_MINAS = "minas"
ALGORITHM_GOIAS = "goias"
ALGORITHM_AMAPA = "amapa"
ALGORITHM_AMAZONAS = "amazonas"

_ASCII_ZERO = ord("0")
#: Bahia picks modulus 10 or 11 from the first digit of the value.
_BAHIA_MODULUS_TEN = frozenset("0123458")


@dataclass(frozen=True, slots=True)
class CheckDigit:
    """One verification digit: which positions feed it, their weights, and how."""

    source: Tuple[int, ...]
    weights: Tuple[int, ...]
    position: int
    modulus: int = 11
    rule: str = RULE_COMPLEMENT
    overflow: str = OVERFLOW_ZERO


@dataclass(frozen=True, slots=True)
class IeLayout:
    """One accepted shape for a state."""

    length: int
    pattern: str
    mask: str
    digits: Tuple[CheckDigit, ...] = ()
    algorithm: str = ALGORITHM_WEIGHTED
    modulus_selector: int = -1


def _descending(first: int, count: int) -> Tuple[int, ...]:
    """Weights counting down from `first`, `count` of them."""
    return tuple(range(first, first - count, -1))


def _run(count: int) -> Tuple[int, ...]:
    """Positions `0 .. count-1`."""
    return tuple(range(count))


def _nine_digit(
    pattern: str,
    mask: str = "#########",
    overflow: str = OVERFLOW_ZERO,
    rule: str = RULE_COMPLEMENT,
) -> Tuple[IeLayout, ...]:
    """The common nine-character shape: one digit over positions 0-7."""
    return (
        IeLayout(
            length=9,
            pattern=pattern,
            mask=mask,
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8, rule=rule, overflow=overflow),),
        ),
    )


STATE_RULES: Dict[str, Tuple[IeLayout, ...]] = {
    "AC": (
        IeLayout(
            length=13,
            pattern=r"^01\d{11}$",
            mask="##.###.###/###-##",
            digits=(
                CheckDigit(source=_run(11), weights=(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=11),
                CheckDigit(source=_run(12), weights=(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=12),
            ),
        ),
    ),
    "AL": _nine_digit(r"^24[03578]\d{6}$", rule=RULE_TIMES_TEN),
    "AM": (
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="##.###.###-#",
            algorithm=ALGORITHM_AMAZONAS,
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8),),
        ),
    ),
    "AP": (
        IeLayout(
            length=9,
            pattern=r"^03\d{7}$",
            mask="#########",
            algorithm=ALGORITHM_AMAPA,
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8),),
        ),
    ),
    "BA": (
        IeLayout(
            length=8,
            pattern=r"^\d{8}$",
            mask="######-##",
            algorithm=ALGORITHM_BAHIA,
            modulus_selector=0,
            digits=(
                CheckDigit(source=_run(6), weights=(7, 6, 5, 4, 3, 2), position=7),
                CheckDigit(source=(0, 1, 2, 3, 4, 5, 7), weights=(8, 7, 6, 5, 4, 3, 2), position=6),
            ),
        ),
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="#######-##",
            algorithm=ALGORITHM_BAHIA,
            modulus_selector=1,
            digits=(
                CheckDigit(source=_run(7), weights=(8, 7, 6, 5, 4, 3, 2), position=8),
                CheckDigit(source=(0, 1, 2, 3, 4, 5, 6, 8), weights=(9, 8, 7, 6, 5, 4, 3, 2), position=7),
            ),
        ),
    ),
    "CE": _nine_digit(r"^\d{9}$", mask="########-#"),
    "DF": (
        IeLayout(
            length=13,
            pattern=r"^07\d{11}$",
            mask="###########-##",
            digits=(
                CheckDigit(source=_run(11), weights=(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=11),
                CheckDigit(source=_run(12), weights=(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=12),
            ),
        ),
    ),
    "ES": _nine_digit(r"^\d{9}$"),
    "GO": (
        IeLayout(
            length=9,
            pattern=r"^1[015]\d{7}$",
            mask="##.###.###-#",
            algorithm=ALGORITHM_GOIAS,
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8),),
        ),
    ),
    "MA": _nine_digit(r"^12\d{7}$"),
    "MG": (
        IeLayout(
            length=13,
            pattern=r"^\d{13}$",
            mask="###.###.###/####",
            algorithm=ALGORITHM_MINAS,
            digits=(
                CheckDigit(source=_run(11), weights=(), position=11),
                CheckDigit(source=_run(12), weights=(3, 2, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2), position=12),
            ),
        ),
    ),
    "MS": _nine_digit(r"^28\d{7}$"),
    "MT": (
        IeLayout(
            length=11,
            pattern=r"^\d{11}$",
            mask="##########-#",
            digits=(CheckDigit(source=_run(10), weights=(3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=10),),
        ),
    ),
    "PA": _nine_digit(r"^15\d{7}$", mask="##-######-#"),
    "PB": _nine_digit(r"^\d{9}$", mask="########-#"),
    "PE": (
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="#######-##",
            digits=(
                CheckDigit(source=_run(7), weights=(8, 7, 6, 5, 4, 3, 2), position=7, overflow=OVERFLOW_SUBTRACT_TEN),
                CheckDigit(source=_run(8), weights=(9, 8, 7, 6, 5, 4, 3, 2), position=8, overflow=OVERFLOW_SUBTRACT_TEN),
            ),
        ),
        IeLayout(
            length=14,
            pattern=r"^\d{14}$",
            mask="##.#.###.#######-#",
            digits=(
                CheckDigit(
                    source=_run(13),
                    weights=(5, 4, 3, 2, 1, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=13,
                    overflow=OVERFLOW_SUBTRACT_TEN,
                ),
            ),
        ),
    ),
    "PI": _nine_digit(r"^\d{9}$"),
    "PR": (
        IeLayout(
            length=10,
            pattern=r"^\d{10}$",
            mask="########-##",
            digits=(
                CheckDigit(source=_run(8), weights=(3, 2, 7, 6, 5, 4, 3, 2), position=8),
                CheckDigit(source=_run(9), weights=(4, 3, 2, 7, 6, 5, 4, 3, 2), position=9),
            ),
        ),
    ),
    "RJ": (
        IeLayout(
            length=8,
            pattern=r"^\d{8}$",
            mask="##.###.##-#",
            digits=(CheckDigit(source=_run(7), weights=(2, 7, 6, 5, 4, 3, 2), position=7),),
        ),
    ),
    "RN": (
        IeLayout(
            length=9,
            pattern=r"^20\d{7}$",
            mask="##.###.###-#",
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8, rule=RULE_TIMES_TEN),),
        ),
        IeLayout(
            length=10,
            pattern=r"^20\d{8}$",
            mask="##.#.###.###-#",
            digits=(CheckDigit(source=_run(9), weights=_descending(10, 9), position=9, rule=RULE_TIMES_TEN),),
        ),
    ),
    "RO": (
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="###.#####-#",
            digits=(CheckDigit(source=(3, 4, 5, 6, 7), weights=(6, 5, 4, 3, 2), position=8, overflow=OVERFLOW_SUBTRACT_TEN),),
        ),
        IeLayout(
            length=14,
            pattern=r"^\d{14}$",
            mask="#############-#",
            digits=(
                CheckDigit(source=_run(13), weights=(6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), position=13, overflow=OVERFLOW_SUBTRACT_TEN),
            ),
        ),
    ),
    "RR": (
        IeLayout(
            length=9,
            pattern=r"^24\d{7}$",
            mask="########-#",
            digits=(CheckDigit(source=_run(8), weights=(1, 2, 3, 4, 5, 6, 7, 8), position=8, modulus=9, rule=RULE_DIRECT),),
        ),
    ),
    "RS": (
        IeLayout(
            length=10,
            pattern=r"^(?:00[1-9]|0[1-9]\d|[1-3]\d\d|4[0-5]\d|46[0-7])\d{7}$",
            mask="###/#######",
            digits=(CheckDigit(source=_run(9), weights=(10, 9, 8, 7, 6, 5, 4, 3, 2), position=9),),
        ),
    ),
    "SC": _nine_digit(r"^\d{9}$", mask="###.###.###"),
    "SE": _nine_digit(r"^\d{9}$"),
    "SP": (
        IeLayout(
            length=12,
            pattern=r"^\d{12}$",
            mask="###.###.###.###",
            digits=(
                CheckDigit(source=_run(8), weights=(1, 3, 4, 5, 6, 7, 8, 10), position=8, rule=RULE_LAST_DIGIT),
                CheckDigit(source=_run(11), weights=(3, 2, 10, 9, 8, 7, 6, 5, 4, 3, 2), position=11, rule=RULE_LAST_DIGIT),
            ),
        ),
        IeLayout(
            length=13,
            pattern=r"^P\d{12}$",
            mask="P-########.#/###",
            digits=(
                CheckDigit(source=tuple(range(1, 9)), weights=(1, 3, 4, 5, 6, 7, 8, 10), position=9, rule=RULE_LAST_DIGIT),
            ),
        ),
    ),
    "TO": (
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="#########",
            digits=(CheckDigit(source=_run(8), weights=_descending(9, 8), position=8),),
        ),
        IeLayout(
            length=11,
            pattern=r"^\d{2}(?:01|02|03|99)\d{7}$",
            mask="###########",
            digits=(CheckDigit(source=(0, 1, 4, 5, 6, 7, 8, 9), weights=_descending(9, 8), position=10),),
        ),
    ),
}

BRAZILIAN_STATES = frozenset(STATE_RULES)
EXEMPT_TOKENS = frozenset({"ISENTO", "ISENTA", "EXEMPT", "NAOCONTRIBUINTE"})


def _clean(value: Any) -> str:
    return "".join(c for c in str(value or "") if c.isalnum()).upper()


def apply_mask(value: str, template: str) -> str:
    """Apply a display mask, consuming one character per `#` in the template."""
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

_PATTERNS: Dict[str, re.Pattern] = {
    layout.pattern: re.compile(layout.pattern)
    for layouts in STATE_RULES.values()
    for layout in layouts
}


def _assert_table_is_sound() -> None:
    """Fail at import when the table is internally inconsistent."""
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


def _pick_layout(uf: str, value: str) -> Tuple[Optional[IeLayout], Tuple[int, ...]]:
    lengths = tuple(layout.length for layout in STATE_RULES[uf])
    for layout in STATE_RULES[uf]:
        if layout.length == len(value) and _PATTERNS[layout.pattern].match(value):
            return layout, lengths
    return None, lengths


def validate_ie(value: Any, uf: Any) -> ValidationResult:
    """Validate a state registration against the rules of its state."""
    state = str(uf or "").strip().upper()[:2]
    if state not in BRAZILIAN_STATES:
        return fail("ie", ErrorCode.UNSUPPORTED_STATE, uf=state)

    raw = str(value or "").strip()
    if not raw:
        return fail("ie", ErrorCode.EMPTY_VALUE, uf=state)

    clean = _clean(raw)
    if clean in EXEMPT_TOKENS:
        return ValidationResult(
            is_valid=True,
            kind="ie",
            clean="ISENTO",
            formatted="ISENTO",
            version="exempt",
            params={"uf": state},
        )

    layout, lengths = _pick_layout(state, clean)
    if layout is None:
        if not any(length == len(clean) for length in lengths):
            return fail(
                "ie", ErrorCode.INVALID_LENGTH, clean=clean, uf=state,
                expected=" / ".join(str(length) for length in lengths), actual=len(clean),
            )
        return fail("ie", ErrorCode.INVALID_FORMAT, clean=clean, uf=state)

    if clean == clean[0] * len(clean):
        return fail("ie", ErrorCode.REPEATED_DIGITS, clean=clean, uf=state)

    compute = _ALGORITHMS[layout.algorithm]
    for order, digit in enumerate(layout.digits, start=1):
        expected = compute(clean, digit, layout)
        if (ord(clean[digit.position]) - _ASCII_ZERO) != expected:
            return fail("ie", ErrorCode.INVALID_CHECKSUM, clean=clean, uf=state, position=order)

    return ok("ie", clean, apply_mask(clean, layout.mask))


__all__ = ["validate_ie", "apply_mask", "STATE_RULES", "BRAZILIAN_STATES", "CheckDigit", "IeLayout"]

"""The 27-state State Registration (Inscrição Estadual) rule table.

Follows the official SINTEGRA layouts for all 27 Brazilian Federation Units.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from dataclasses import dataclass
from typing import Dict, Tuple

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


@dataclass(frozen=True, slots=True)
class CheckDigit:
    """One verification digit definition: source indices, weights, and algorithm parameters."""

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
    return tuple(range(first, first - count, -1))


def _run(count: int) -> Tuple[int, ...]:
    return tuple(range(count))


def _nine_digit(
    pattern: str,
    mask: str = "#########",
    overflow: str = OVERFLOW_ZERO,
    rule: str = RULE_COMPLEMENT,
) -> Tuple[IeLayout, ...]:
    return (
        IeLayout(
            length=9,
            pattern=pattern,
            mask=mask,
            digits=(
                CheckDigit(
                    source=_run(8),
                    weights=_descending(9, 8),
                    position=8,
                    rule=rule,
                    overflow=overflow,
                ),
            ),
        ),
    )


STATE_RULES: Dict[str, Tuple[IeLayout, ...]] = {
    "AC": (
        IeLayout(
            length=13,
            pattern=r"^01\d{11}$",
            mask="##.###.###/###-##",
            digits=(
                CheckDigit(
                    source=_run(11),
                    weights=(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=11,
                ),
                CheckDigit(
                    source=_run(12),
                    weights=(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=12,
                ),
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
                CheckDigit(
                    source=(0, 1, 2, 3, 4, 5, 7),
                    weights=(8, 7, 6, 5, 4, 3, 2),
                    position=6,
                ),
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
                CheckDigit(
                    source=(0, 1, 2, 3, 4, 5, 6, 8),
                    weights=(9, 8, 7, 6, 5, 4, 3, 2),
                    position=7,
                ),
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
                CheckDigit(
                    source=_run(11),
                    weights=(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=11,
                ),
                CheckDigit(
                    source=_run(12),
                    weights=(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=12,
                ),
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
                CheckDigit(
                    source=_run(12),
                    weights=(3, 2, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=12,
                ),
            ),
        ),
    ),
    "MS": _nine_digit(r"^28\d{7}$"),
    "MT": (
        IeLayout(
            length=11,
            pattern=r"^\d{11}$",
            mask="##########-#",
            digits=(
                CheckDigit(
                    source=_run(10),
                    weights=(3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=10,
                ),
            ),
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
                CheckDigit(
                    source=_run(7),
                    weights=(8, 7, 6, 5, 4, 3, 2),
                    position=7,
                    overflow=OVERFLOW_SUBTRACT_TEN,
                ),
                CheckDigit(
                    source=_run(8),
                    weights=(9, 8, 7, 6, 5, 4, 3, 2),
                    position=8,
                    overflow=OVERFLOW_SUBTRACT_TEN,
                ),
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
            digits=(
                CheckDigit(
                    source=_run(8),
                    weights=_descending(9, 8),
                    position=8,
                    rule=RULE_TIMES_TEN,
                ),
            ),
        ),
        IeLayout(
            length=10,
            pattern=r"^20\d{8}$",
            mask="##.#.###.###-#",
            digits=(
                CheckDigit(
                    source=_run(9),
                    weights=_descending(10, 9),
                    position=9,
                    rule=RULE_TIMES_TEN,
                ),
            ),
        ),
    ),
    "RO": (
        IeLayout(
            length=9,
            pattern=r"^\d{9}$",
            mask="###.#####-#",
            digits=(
                CheckDigit(
                    source=(3, 4, 5, 6, 7),
                    weights=(6, 5, 4, 3, 2),
                    position=8,
                    overflow=OVERFLOW_SUBTRACT_TEN,
                ),
            ),
        ),
        IeLayout(
            length=14,
            pattern=r"^\d{14}$",
            mask="#############-#",
            digits=(
                CheckDigit(
                    source=_run(13),
                    weights=(6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=13,
                    overflow=OVERFLOW_SUBTRACT_TEN,
                ),
            ),
        ),
    ),
    "RR": (
        IeLayout(
            length=9,
            pattern=r"^24\d{7}$",
            mask="########-#",
            digits=(
                CheckDigit(
                    source=_run(8),
                    weights=(1, 2, 3, 4, 5, 6, 7, 8),
                    position=8,
                    modulus=9,
                    rule=RULE_DIRECT,
                ),
            ),
        ),
    ),
    "RS": (
        IeLayout(
            length=10,
            pattern=r"^(?:00[1-9]|0[1-9]\d|[1-3]\d\d|4[0-5]\d|46[0-7])\d{7}$",
            mask="###/#######",
            digits=(
                CheckDigit(
                    source=_run(9),
                    weights=(10, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=9,
                ),
            ),
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
                CheckDigit(
                    source=_run(8),
                    weights=(1, 3, 4, 5, 6, 7, 8, 10),
                    position=8,
                    rule=RULE_LAST_DIGIT,
                ),
                CheckDigit(
                    source=_run(11),
                    weights=(3, 2, 10, 9, 8, 7, 6, 5, 4, 3, 2),
                    position=11,
                    rule=RULE_LAST_DIGIT,
                ),
            ),
        ),
        IeLayout(
            length=13,
            pattern=r"^P\d{12}$",
            mask="P-########.#/###",
            digits=(
                CheckDigit(
                    source=tuple(range(1, 9)),
                    weights=(1, 3, 4, 5, 6, 7, 8, 10),
                    position=9,
                    rule=RULE_LAST_DIGIT,
                ),
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
            digits=(
                CheckDigit(
                    source=(0, 1, 4, 5, 6, 7, 8, 9),
                    weights=_descending(9, 8),
                    position=10,
                ),
            ),
        ),
    ),
}

BRAZILIAN_STATES = frozenset(STATE_RULES)
EXEMPT_TOKENS = frozenset({"ISENTO", "ISENTA", "EXEMPT", "NAOCONTRIBUINTE"})

__all__ = [
    "STATE_RULES",
    "BRAZILIAN_STATES",
    "EXEMPT_TOKENS",
    "CheckDigit",
    "IeLayout",
    "OVERFLOW_ZERO",
    "OVERFLOW_ONE",
    "OVERFLOW_SUBTRACT_TEN",
    "RULE_COMPLEMENT",
    "RULE_DIRECT",
    "RULE_TIMES_TEN",
    "RULE_LAST_DIGIT",
    "ALGORITHM_WEIGHTED",
    "ALGORITHM_BAHIA",
    "ALGORITHM_MINAS",
    "ALGORITHM_GOIAS",
    "ALGORITHM_AMAPA",
    "ALGORITHM_AMAZONAS",
]

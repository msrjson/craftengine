"""Stable machine error codes for Brazilian document validation and normalization."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from enum import Enum


class ErrorCode(str, Enum):
    """Machine-readable validation error codes."""

    EMPTY_VALUE = "EMPTY_VALUE"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_FORMAT = "INVALID_FORMAT"
    REPEATED_DIGITS = "REPEATED_DIGITS"
    INVALID_CHECKSUM = "INVALID_CHECKSUM"
    UNSUPPORTED_STATE = "UNSUPPORTED_STATE"
    UNKNOWN_VERSION = "UNKNOWN_VERSION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# Backwards compatibility constants
EMPTY_VALUE = ErrorCode.EMPTY_VALUE
INVALID_LENGTH = ErrorCode.INVALID_LENGTH
INVALID_FORMAT = ErrorCode.INVALID_FORMAT
REPEATED_DIGITS = ErrorCode.REPEATED_DIGITS
INVALID_CHECKSUM = ErrorCode.INVALID_CHECKSUM
UNSUPPORTED_STATE = ErrorCode.UNSUPPORTED_STATE
UNKNOWN_VERSION = ErrorCode.UNKNOWN_VERSION
UNKNOWN_ERROR = ErrorCode.UNKNOWN_ERROR

ERROR_CODES = frozenset(ErrorCode)

__all__ = ["ErrorCode", "ERROR_CODES"]

"""Stable machine codes for Brazilian document validation and normalization.

The codes, not the sentences, are the contract: a caller branches on
`ErrorCode` and renders copy from `message_key`, so the wording can be
translated or rewritten without touching the validation logic.
"""

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


__all__ = ["ErrorCode"]

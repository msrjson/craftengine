"""DocumentSeal — a tamper-evident digest of a document.

Sealing stores a digest, never the document; verifying recomputes the digest
from the content and compares, so any change to the content is detected. A
keyed seal uses HMAC, so the digest cannot be recomputed by anyone who does not
hold the key.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Union

ALGORITHM = "sha256"
BytesLike = Union[str, bytes, bytearray]


@dataclass(frozen=True, slots=True)
class Seal:
    """How a document was sealed, its digest, and when."""

    algorithm: str
    digest: str
    sealed_at: str
    keyed: bool = False


class DocumentSeal:
    """Stateless document sealing and verification. Pure functions."""

    @staticmethod
    def _data(content: BytesLike) -> bytes:
        return content.encode("utf-8") if isinstance(content, str) else bytes(content)

    @staticmethod
    def seal(content: BytesLike, key: Optional[str] = None) -> Seal:
        """Return the seal of `content`; a non-empty `key` makes it an HMAC."""
        data = DocumentSeal._data(content)
        if key:
            digest = hmac.new(key.encode("utf-8"), data, hashlib.sha256).hexdigest()
        else:
            digest = hashlib.sha256(data).hexdigest()
        sealed_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        return Seal(algorithm=ALGORITHM, digest=digest, sealed_at=sealed_at, keyed=bool(key))

    @staticmethod
    def verify(content: BytesLike, seal: Seal, key: Optional[str] = None) -> bool:
        """Whether `content` still matches `seal` under the same key."""
        if seal.algorithm != ALGORITHM:
            return False
        if seal.keyed and not key:
            return False
        recomputed = DocumentSeal.seal(content, key if seal.keyed else None)
        return hmac.compare_digest(recomputed.digest, seal.digest)


__all__ = ["DocumentSeal", "Seal", "ALGORITHM"]

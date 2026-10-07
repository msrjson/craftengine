"""Certificate-authenticated (mTLS) channel: build a client TLS context.

A peer that authenticates callers with a certificate — a bank, a tax authority —
needs both sides to present one. `ssl_context()` returns a context carrying the
client certificate, ready for an HTTP client to open an authenticated
connection.

The private key never durably touches disk. Python's TLS loader reads a
certificate only from a path, never from memory, so the pair is written to a
temporary file created `0600` from the start, loaded, and removed in the same
block; the context then keeps the key in memory. The ready context is cached by
a fingerprint of the material, so that file window does not reopen on every
call, and replacing one certificate invalidates only that context. Server
verification stays on — turning it off would make mTLS theatre.

A refusal is typed: `ChannelError` carries a stable `code`, a `message_key` and
its parameters, never a sentence.
"""

from __future__ import annotations

import hashlib
import os
import ssl
import tempfile
import threading
from typing import Any, Dict

#: Ready contexts, keyed by a fingerprint of the material they carry.
_contexts: Dict[str, ssl.SSLContext] = {}
_lock = threading.Lock()


class ChannelError(RuntimeError):
    """The certificate-authenticated channel could not be established."""

    def __init__(self, code: str, message_key: str, detail: str = "", **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.message_key = message_key
        #: The loader's own words, for the log. Never rendered to a user.
        self.detail = detail
        self.params = params


def _fingerprint(*parts: str) -> str:
    """Return a stable digest of the material, never the material itself."""
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def _write_private(path: str, content: str) -> None:
    """Write PEM material with `0600` permissions from creation."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content if content.endswith("\n") else content + "\n")


def _discard(*paths: str) -> None:
    """Remove temporary material, ignoring what is already gone."""
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


def _load(context: ssl.SSLContext, certificate_pem: str, private_key_pem: str, key_password: str) -> None:
    """Load the pair through a short-lived private file with `0600` from birth."""
    folder = tempfile.mkdtemp(prefix="craft-mtls-")
    certificate_path = os.path.join(folder, "cert.pem")
    key_path = os.path.join(folder, "key.pem")
    try:
        _write_private(certificate_path, certificate_pem)
        _write_private(key_path, private_key_pem)
        context.load_cert_chain(
            certfile=certificate_path, keyfile=key_path, password=(key_password or None)
        )
    except ssl.SSLError as refusal:
        raise ChannelError(
            "CHANNEL_PAIR_REJECTED", "mtls.errors.pair_rejected", detail=str(refusal)
        ) from refusal
    finally:
        _discard(key_path, certificate_path)
        try:
            os.rmdir(folder)
        except OSError:
            pass


def ssl_context(certificate_pem: str, private_key_pem: str, key_password: str = "") -> ssl.SSLContext:
    """Return a TLS context carrying the client certificate, cached by material.

    Args:
        certificate_pem: Certificate material, PEM encoded.
        private_key_pem: Private key material, PEM encoded. It may be the same
            bundle as the certificate (an A1 container is stored that way).
        key_password: Passphrase of the key, empty when it has none.

    Returns:
        A context ready to open an authenticated connection.

    Raises:
        ChannelError: `CHANNEL_MATERIAL_MISSING` when either side of the pair is
            absent, or `CHANNEL_PAIR_REJECTED` when the pair is not accepted.
    """
    certificate_pem = (certificate_pem or "").strip()
    private_key_pem = (private_key_pem or "").strip()
    if not certificate_pem or not private_key_pem:
        raise ChannelError("CHANNEL_MATERIAL_MISSING", "mtls.errors.material_missing")

    mark = _fingerprint(certificate_pem, private_key_pem, key_password or "")
    with _lock:
        ready = _contexts.get(mark)
        if ready is not None:
            return ready
        context = ssl.create_default_context()
        _load(context, certificate_pem, private_key_pem, key_password or "")
        _contexts[mark] = context
        return context


def ssl_context_from_files(certificate_path: str, private_key_path: str, key_password: str = "") -> ssl.SSLContext:
    """Read a PEM pair from disk and return its context.

    Raises:
        ChannelError: `CHANNEL_MATERIAL_MISSING` when a file cannot be read.
    """
    try:
        with open(certificate_path, "r", encoding="utf-8") as handle:
            certificate_pem = handle.read()
        with open(private_key_path, "r", encoding="utf-8") as handle:
            private_key_pem = handle.read()
    except OSError as error:
        raise ChannelError(
            "CHANNEL_MATERIAL_MISSING", "mtls.errors.material_missing", detail=str(error)
        ) from error
    return ssl_context(certificate_pem, private_key_pem, key_password)


def forget_contexts() -> None:
    """Discard the cached contexts; used when a certificate is replaced, and in tests."""
    with _lock:
        _contexts.clear()


__all__ = ["ssl_context", "ssl_context_from_files", "forget_contexts", "ChannelError"]

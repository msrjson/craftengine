"""Mutual TLS channel — plugin descriptor and registration."""

from plugins.mtls.channel import (
    ChannelError,
    forget_contexts,
    ssl_context,
    ssl_context_from_files,
)

PLUGIN = {
    "slug": "mtls",
    "name": "Mutual TLS Channel",
    "version": "1.0.0",
    "description": (
        "Build a certificate-authenticated TLS context from a client certificate "
        "and key, without the private key durably touching disk."
    ),
}


class MutualTlsChannel:
    """The mTLS capability an application reaches through the container."""

    error = ChannelError
    context = staticmethod(ssl_context)
    context_from_files = staticmethod(ssl_context_from_files)
    forget = staticmethod(forget_contexts)


def register(app) -> None:
    """Bind the mTLS channel into the application container."""
    container = getattr(app, "container", None) or app
    if hasattr(container, "singleton"):
        container.singleton("mtls", lambda _container: MutualTlsChannel())


__all__ = [
    "PLUGIN",
    "register",
    "MutualTlsChannel",
    "ssl_context",
    "ssl_context_from_files",
    "forget_contexts",
    "ChannelError",
]

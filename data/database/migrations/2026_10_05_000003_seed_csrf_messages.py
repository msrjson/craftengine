"""Migration: the CSRF refusals' messages, in every offered locale.

`VerifyCsrfToken` answers 403 `CSRF_ORIGIN_REJECTED` and 419
`CSRF_TOKEN_MISMATCH` with a `message_key` instead of a hardcoded English
sentence. A row that already exists is left alone.

Forward-only: there is no `down()`; translations are never deleted.

Category: Framework schema (security).
"""

from craft.facades import DB

#: (key, locale, value). `en` is the source, `pt-BR` the default, `es` the alternative.
ROWS = [
    ("security.csrf.origin_rejected", "en", "This form was sent from another site, so it was not accepted."),
    ("security.csrf.origin_rejected", "pt-BR", "Este formulário veio de outro site e por isso não foi aceito."),
    ("security.csrf.origin_rejected", "es", "Este formulario se envió desde otro sitio, por eso no se aceptó."),
    ("security.csrf.token_mismatch", "en", "This page expired. Reload it and send the form again."),
    ("security.csrf.token_mismatch", "pt-BR", "Esta página expirou. Recarregue e envie o formulário de novo."),
    ("security.csrf.token_mismatch", "es", "Esta página caducó. Recarga y envía el formulario de nuevo."),
]


def up():
    for key, locale, value in ROWS:
        if DB.table("translations").where("key", key).where("locale", locale).first() is None:
            DB.table("translations").insert({"key": key, "locale": locale, "value": value})

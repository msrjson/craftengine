"""Validation messages: translation keys, their seed rows and the fallback.

Every message the `Validator` produces is the translation key
`validation.<code>`, formatted with ICU named placeholders (`{field}` and the
rule's own values). A project seeds the rows once (`seed_translations()`, run
by the migration `craft new` writes), after which the copy is the project's
to edit in the database. When a key has no row in any locale, the English
source text below is used, so validation never shows a raw key.

The table is seed input and last-resort fallback, not the source of truth:
the `translations` table is.

Category: Core Framework (Validation).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any

#: code -> (en, pt-BR, es). `en` is the source locale and the fallback.
TRANSLATIONS = {
    "required": ("{field} is required", "O campo {field} é obrigatório", "El campo {field} es obligatorio"),
    "prohibited": ("{field} is prohibited", "O campo {field} não é permitido", "El campo {field} no está permitido"),
    "honeypot": ("Automated submission rejected", "Envio automatizado recusado", "Envío automatizado rechazado"),
    "invalid": ("{field} is invalid", "O campo {field} é inválido", "El campo {field} no es válido"),
    "string": ("{field} must be a string", "O campo {field} deve ser um texto", "El campo {field} debe ser un texto"),
    "integer": ("{field} must be an integer", "O campo {field} deve ser um número inteiro", "El campo {field} debe ser un número entero"),
    "numeric": ("{field} must be numeric", "O campo {field} deve ser numérico", "El campo {field} debe ser numérico"),
    "boolean": ("{field} must be a boolean", "O campo {field} deve ser verdadeiro ou falso", "El campo {field} debe ser verdadero o falso"),
    "array": ("{field} must be an array", "O campo {field} deve ser uma lista", "El campo {field} debe ser una lista"),
    "date": ("{field} must be a valid date", "O campo {field} deve ser uma data válida", "El campo {field} debe ser una fecha válida"),
    "email": (
        "{field} must be a valid email address",
        "O campo {field} deve ser um endereço de e-mail válido",
        "El campo {field} debe ser una dirección de correo válida",
    ),
    "url": ("{field} must be a valid URL", "O campo {field} deve ser uma URL válida", "El campo {field} debe ser una URL válida"),
    "uuid": ("{field} must be a valid UUID", "O campo {field} deve ser um UUID válido", "El campo {field} debe ser un UUID válido"),
    "alpha": ("{field} must contain only letters", "O campo {field} deve conter apenas letras", "El campo {field} solo puede contener letras"),
    "alpha_num": ("{field} must be alphanumeric", "O campo {field} deve conter apenas letras e números", "El campo {field} solo puede contener letras y números"),
    "alpha_dash": (
        "{field} may contain only letters, numbers, dashes and underscores",
        "O campo {field} pode conter apenas letras, números, hífens e sublinhados",
        "El campo {field} solo puede contener letras, números, guiones y guiones bajos",
    ),
    "alpha_spaces": (
        "{field} may contain only letters and spaces",
        "O campo {field} pode conter apenas letras e espaços",
        "El campo {field} solo puede contener letras y espacios",
    ),
    "regex": ("{field} format is invalid", "O formato do campo {field} é inválido", "El formato del campo {field} no es válido"),
    "ip": ("{field} must be a valid IP address", "O campo {field} deve ser um endereço IP válido", "El campo {field} debe ser una dirección IP válida"),
    "ipv4": ("{field} must be a valid IPv4 address", "O campo {field} deve ser um endereço IPv4 válido", "El campo {field} debe ser una dirección IPv4 válida"),
    "ipv6": ("{field} must be a valid IPv6 address", "O campo {field} deve ser um endereço IPv6 válido", "El campo {field} debe ser una dirección IPv6 válida"),
    "json": ("{field} must be a valid JSON string", "O campo {field} deve ser um JSON válido", "El campo {field} debe ser un JSON válido"),
    "digits": ("{field} must be {length} digits", "O campo {field} deve ter {length} dígitos", "El campo {field} debe tener {length} dígitos"),
    "digits_between": (
        "{field} must be between {min} and {max} digits",
        "O campo {field} deve ter entre {min} e {max} dígitos",
        "El campo {field} debe tener entre {min} y {max} dígitos",
    ),
    "decimal": ("{field} must be a valid decimal", "O campo {field} deve ser um decimal válido", "El campo {field} debe ser un decimal válido"),
    "decimal_places": (
        "{field} must have exactly {expected} decimal places",
        "O campo {field} deve ter exatamente {expected} casas decimais",
        "El campo {field} debe tener exactamente {expected} decimales",
    ),
    "starts_with": (
        "{field} must start with one of: {values}",
        "O campo {field} deve começar com um destes: {values}",
        "El campo {field} debe empezar con uno de: {values}",
    ),
    "ends_with": (
        "{field} must end with one of: {values}",
        "O campo {field} deve terminar com um destes: {values}",
        "El campo {field} debe terminar con uno de: {values}",
    ),
    "timezone": ("{field} must be a valid timezone", "O campo {field} deve ser um fuso horário válido", "El campo {field} debe ser una zona horaria válida"),
    "spam_free": ("{field} contains detected spam content", "O campo {field} contém conteúdo identificado como spam", "El campo {field} contiene contenido detectado como spam"),
    "no_html": ("{field} must not contain HTML tags", "O campo {field} não pode conter tags HTML", "El campo {field} no puede contener etiquetas HTML"),
    "text": ("{field} must be plain text without HTML", "O campo {field} deve ser texto simples, sem HTML", "El campo {field} debe ser texto plano, sin HTML"),
    "file": ("{field} must be an uploaded file", "O campo {field} deve ser um arquivo enviado", "El campo {field} debe ser un archivo subido"),
    "image": ("{field} must be an image", "O campo {field} deve ser uma imagem", "El campo {field} debe ser una imagen"),
    "image_type": ("{field} must be an image ({types})", "O campo {field} deve ser uma imagem ({types})", "El campo {field} debe ser una imagen ({types})"),
    "mimes": (
        "{field} must be a file of type: {values}",
        "O campo {field} deve ser um arquivo do tipo: {values}",
        "El campo {field} debe ser un archivo de tipo: {values}",
    ),
    "max_file_size": (
        "{field} may not be greater than {value} kilobytes",
        "O campo {field} não pode ter mais de {value} kilobytes",
        "El campo {field} no puede superar {value} kilobytes",
    ),
    "min_file_size": (
        "{field} must be at least {value} kilobytes",
        "O campo {field} deve ter pelo menos {value} kilobytes",
        "El campo {field} debe tener al menos {value} kilobytes",
    ),
    "min": ("{field} must be at least {value}", "O campo {field} deve ser no mínimo {value}", "El campo {field} debe ser al menos {value}"),
    "max": ("{field} may not be greater than {value}", "O campo {field} não pode ser maior que {value}", "El campo {field} no puede ser mayor que {value}"),
    "between": ("{field} must be between {min} and {max}", "O campo {field} deve estar entre {min} e {max}", "El campo {field} debe estar entre {min} y {max}"),
    "size": ("{field} must be {value}", "O campo {field} deve ser {value}", "El campo {field} debe ser {value}"),
    "in": ("{field} must be one of: {values}", "O campo {field} deve ser um destes: {values}", "El campo {field} debe ser uno de: {values}"),
    "not_in": ("{field} must not be one of: {values}", "O campo {field} não pode ser um destes: {values}", "El campo {field} no puede ser uno de: {values}"),
    "same": ("{field} must match {value}", "O campo {field} deve ser igual a {value}", "El campo {field} debe coincidir con {value}"),
    "different": ("{field} must be different from {value}", "O campo {field} deve ser diferente de {value}", "El campo {field} debe ser distinto de {value}"),
    "confirmed": ("{field} confirmation does not match", "A confirmação do campo {field} não confere", "La confirmación del campo {field} no coincide"),
    "accepted": ("{field} must be accepted", "O campo {field} deve ser aceito", "El campo {field} debe ser aceptado"),
    "unique": ("{field} has already been taken", "O valor do campo {field} já está em uso", "El valor del campo {field} ya está en uso"),
    "exists": ("selected {field} is invalid", "O {field} selecionado é inválido", "El {field} seleccionado no es válido"),
}

KEY_PREFIX = "validation."
LOCALES = ("en", "pt-BR", "es")


def message(code: str, **params: Any) -> str:
    """Return the validation message for `code` in the active locale.

    Args:
        code: A key of `TRANSLATIONS`.
        **params: The values the message names, `field` included.

    Returns:
        The translated message, or the English source text when no locale has
        a row for the key.
    """
    from engine.support.translation import translate

    key = KEY_PREFIX + code
    text = translate(key, **params)
    if text != key:
        return text
    from engine.support.icu import format_message

    return format_message(TRANSLATIONS[code][0], params, locale="en")


def seed_translations(db: Any) -> int:
    """Insert every validation key in every locale where it is absent.

    Args:
        db: The database manager (`DB` facade or `app.make("db")`).

    Returns:
        How many rows were inserted. Existing rows are never changed.
    """
    inserted = 0
    for code, values in TRANSLATIONS.items():
        for locale, value in zip(LOCALES, values, strict=True):
            key = KEY_PREFIX + code
            if db.table("translations").where("key", key).where("locale", locale).first() is None:
                db.table("translations").insert({"key": key, "locale": locale, "value": value})
                inserted += 1
    return inserted


__all__ = ["KEY_PREFIX", "LOCALES", "TRANSLATIONS", "message", "seed_translations"]

"""Validator for Craft Framework.

Rules are given per field as a list or a pipe-delimited string::

    Validator(data, {
        "name":     ["required", "string", "max:255"],
        "email":    "required|email|unique:users,email",
        "age":      ["nullable", "integer", "between:18,120"],
        "password": ["required", "min:8", "confirmed"],
    })

Category: Core Framework (Validation).
Relations:
  - Used directly, or through `engine/validation/form_request.py`; database
    rules (`unique`, `exists`) resolve `db` via `Container.getInstance()`.
References:
  - Guide: `documentation/validation.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Reused rather than reimplemented: `unique`/`exists` interpolate their table
# and column arguments into SQL, so they need the same allowlist the query
# builder applies to every identifier it writes.
from engine.orm.query_builder import _assert_identifier

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
ALPHA_RE = re.compile(r"^[a-zA-Z]+$")
ALPHA_NUM_RE = re.compile(r"^[a-zA-Z0-9]+$")
ALPHA_DASH_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico", "tiff"}

from engine.validation.error_bag import MessageBag, ViewErrorBag

Rules = Dict[str, Union[str, List[Any]]]


class Validator:
    """Validates a data bag against a rule set."""

    #: Registry for application-defined and plugin validation rules.
    _custom_rules: Dict[str, Tuple[Callable, Optional[str]]] = {}

    def __init__(
        self,
        data: Dict[str, Any],
        rules: Rules,
        messages: Optional[Dict[str, str]] = None,
    ):
        self.data = data or {}
        self.rules = rules or {}
        self.messages = messages or {}
        self.errors: MessageBag = MessageBag()
        self._validate()

    @classmethod
    def extend(cls, name: str, handler: Callable, message: Optional[str] = None) -> None:
        """Register a custom validation rule.

        Handler signature: (field: str, value: Any, args: List[str], validator: Validator) -> bool
        """
        cls._custom_rules[name.strip().lower()] = (handler, message)

    # -- rule parsing ----------------------------------------------------------

    @staticmethod
    def _normalise(rule_list: Union[str, List[Any]]) -> List[str]:
        if isinstance(rule_list, str):
            return [r for r in rule_list.split("|") if r]
        return [r for r in rule_list if r]

    @staticmethod
    def _split(rule: str):
        name, _, argument = str(rule).partition(":")
        args = [a.strip() for a in argument.split(",")] if argument else []
        return name.strip().lower(), args

    # -- driving ---------------------------------------------------------------

    def _validate(self) -> None:
        for field, rule_list in self.rules.items():
            rules = self._normalise(rule_list)
            value = self.data.get(field)

            present = (
                field in self.data
                and value not in (None, "")
                and (not hasattr(value, "filename") or bool(getattr(value, "filename", "")))
            )
            nullable = any(self._split(r)[0] == "nullable" for r in rules)

            for rule in rules:
                name, args = self._split(rule)

                if name in ("nullable", "sometimes"):
                    continue

                # Presence rules and prohibited/honeypot rules must inspect both present and absent values.
                if not present and not name.startswith("required") and not name.startswith("prohibited") and name != "honeypot":
                    continue
                if not present and nullable and not name.startswith("prohibited"):
                    continue

                handler: Optional[Callable] = getattr(self, f"_rule_{name}", None)
                if handler is not None:
                    handler(field, value, args)
                elif name in self._custom_rules:
                    callback, default_msg = self._custom_rules[name]
                    passed = callback(field, value, args, self)
                    if not passed:
                        if default_msg:
                            self.errors.setdefault(field, []).append(
                                self.messages.get(".".join((field, name))) or default_msg
                            )
                        else:
                            self._add_error(field, name, code="invalid")
                else:
                    # A typo'd rule that silently does nothing is worse than a
                    # loud failure — the field looks validated but is not.
                    raise ValueError(
                        f"Unknown validation rule [{name}] on field [{field}]."
                    )

    def _add_error(self, field: str, rule: str, code: Optional[str] = None, **params: Any) -> None:
        """Record a failure of `rule` on `field`.

        A message the caller gave for `field.rule` or `field` wins; otherwise
        the text is the translation key `validation.<code>` (`code` defaults
        to the rule), formatted with `field` and `params`.
        """
        custom = self.messages.get(".".join((field, rule))) or self.messages.get(field)
        if custom:
            self.errors.setdefault(field, []).append(custom)
            return
        from engine.validation.messages import message

        self.errors.setdefault(field, []).append(message(code or rule, field=field, **params))

    # -- presence --------------------------------------------------------------

    def _rule_required(self, field: str, value: Any, args: List[str]) -> None:
        if value is None or value == "" or value == [] or value == {}:
            self._add_error(field, "required")
            return
        if hasattr(value, "filename") and not getattr(value, "filename", ""):
            self._add_error(field, "required")

    def _rule_required_if(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2 and str(self.data.get(args[0])) == args[1]:
            self._rule_required(field, value, [])

    def _rule_required_with(self, field: str, value: Any, args: List[str]) -> None:
        if any(self.data.get(other) not in (None, "") for other in args):
            self._rule_required(field, value, [])

    def _rule_required_without(self, field: str, value: Any, args: List[str]) -> None:
        if any(self.data.get(other) in (None, "", [], {}) for other in args):
            self._rule_required(field, value, [])

    def _rule_required_without_all(self, field: str, value: Any, args: List[str]) -> None:
        if all(self.data.get(other) in (None, "", [], {}) for other in args):
            self._rule_required(field, value, [])

    def _rule_prohibited(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (None, "", [], {}):
            self._add_error(field, "prohibited")

    def _rule_prohibited_if(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2 and str(self.data.get(args[0])) == args[1]:
            self._rule_prohibited(field, value, [])

    def _rule_prohibited_unless(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2 and str(self.data.get(args[0])) != args[1]:
            self._rule_prohibited(field, value, [])

    def _rule_honeypot(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (None, ""):
            self._add_error(field, "honeypot")

    # -- types -----------------------------------------------------------------

    def _rule_string(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, str):
            self._add_error(field, "string")

    def _rule_integer(self, field: str, value: Any, args: List[str]) -> None:
        # bool is a subclass of int — accepting True as an integer is a bug.
        if isinstance(value, bool) or not isinstance(value, int):
            if not (isinstance(value, str) and value.lstrip("-").isdigit()):
                self._add_error(field, "integer")

    def _rule_numeric(self, field: str, value: Any, args: List[str]) -> None:
        if isinstance(value, bool):
            self._add_error(field, "numeric")
            return
        if isinstance(value, (int, float)):
            return
        try:
            float(value)
        except (TypeError, ValueError):
            self._add_error(field, "numeric")

    def _rule_boolean(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (True, False, 0, 1, "0", "1", "true", "false"):
            self._add_error(field, "boolean")

    def _rule_array(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, (list, tuple)):
            self._add_error(field, "array")

    def _rule_date(self, field: str, value: Any, args: List[str]) -> None:
        from datetime import date, datetime

        if isinstance(value, (date, datetime)):
            return
        try:
            datetime.fromisoformat(str(value))
        except ValueError:
            self._add_error(field, "date")

    # -- formats ---------------------------------------------------------------

    def _pattern(self, field: str, value: Any, pattern: Any, rule: str) -> None:
        if not isinstance(value, str) or not pattern.match(value):
            self._add_error(field, rule)

    def _rule_email(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, EMAIL_RE, "email")

    def _rule_url(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, URL_RE, "url")

    def _rule_uuid(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, UUID_RE, "uuid")

    def _rule_alpha(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, ALPHA_RE, "alpha")

    def _rule_alpha_num(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, ALPHA_NUM_RE, "alpha_num")

    def _rule_alpha_dash(self, field: str, value: Any, args: List[str]) -> None:
        self._pattern(field, value, ALPHA_DASH_RE, "alpha_dash")

    def _rule_regex(self, field: str, value: Any, args: List[str]) -> None:
        if not args:
            return
        if not isinstance(value, str) or not re.search(args[0], value):
            self._add_error(field, "regex")

    def _rule_ip(self, field: str, value: Any, args: List[str]) -> None:
        import ipaddress

        try:
            ipaddress.ip_address(str(value))
        except ValueError:
            self._add_error(field, "ip")

    def _rule_ipv4(self, field: str, value: Any, args: List[str]) -> None:
        import ipaddress

        try:
            addr = ipaddress.ip_address(str(value))
            if addr.version != 4:
                self._add_error(field, "ipv4")
        except ValueError:
            self._add_error(field, "ipv4")

    def _rule_ipv6(self, field: str, value: Any, args: List[str]) -> None:
        import ipaddress

        try:
            addr = ipaddress.ip_address(str(value))
            if addr.version != 6:
                self._add_error(field, "ipv6")
        except ValueError:
            self._add_error(field, "ipv6")

    def _rule_json(self, field: str, value: Any, args: List[str]) -> None:
        import json

        if not isinstance(value, str):
            self._add_error(field, "json")
            return
        try:
            json.loads(value)
        except (ValueError, TypeError):
            self._add_error(field, "json")

    def _rule_digits(self, field: str, value: Any, args: List[str]) -> None:
        s = str(value)
        if not s.isdigit() or (args and len(s) != int(args[0])):
            length = args[0] if args else "specified"
            self._add_error(field, "digits", length=length)

    def _rule_digits_between(self, field: str, value: Any, args: List[str]) -> None:
        s = str(value)
        if not s.isdigit() or len(args) < 2 or len(s) < int(args[0]) or len(s) > int(args[1]):
            self._add_error(field, "digits_between", min=args[0], max=args[1])

    def _rule_decimal(self, field: str, value: Any, args: List[str]) -> None:
        s = str(value)
        try:
            float(s)
        except (ValueError, TypeError):
            self._add_error(field, "decimal")
            return
        if "." in s and args:
            decimals = len(s.split(".", 1)[1])
            expected = int(args[0])
            if decimals != expected:
                self._add_error(field, "decimal", code="decimal_places", expected=expected)

    def _rule_starts_with(self, field: str, value: Any, args: List[str]) -> None:
        s = str(value)
        if not any(s.startswith(prefix) for prefix in args):
            self._add_error(field, "starts_with", values=', '.join(args))

    def _rule_ends_with(self, field: str, value: Any, args: List[str]) -> None:
        s = str(value)
        if not any(s.endswith(suffix) for suffix in args):
            self._add_error(field, "ends_with", values=', '.join(args))

    def _rule_timezone(self, field: str, value: Any, args: List[str]) -> None:
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(str(value))
        except Exception:
            self._add_error(field, "timezone")

    def _rule_spam_free(self, field: str, value: Any, args: List[str]) -> None:
        from engine.security.antispam import AntiSpamService

        antispam = AntiSpamService()
        score, reasons = antispam.analyze_content({field: str(value)})
        threshold = float(args[0]) if args else 0.7
        if score >= threshold:
            self._add_error(field, "spam_free")

    # -- text and sanitization -------------------------------------------------

    def _rule_alpha_spaces(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, str) or not value.strip() or not all(c.isalpha() or c.isspace() for c in value):
            self._add_error(field, "alpha_spaces")

    def _rule_no_html(self, field: str, value: Any, args: List[str]) -> None:
        if not isinstance(value, str) or HTML_TAG_RE.search(value):
            self._add_error(field, "no_html")

    def _rule_text(self, field: str, value: Any, args: List[str]) -> None:
        """Ensures input is plain readable text with no HTML tags or script injection."""
        if not isinstance(value, str) or HTML_TAG_RE.search(value):
            self._add_error(field, "text")

    # -- files and uploads -----------------------------------------------------

    @staticmethod
    def _extract_file_meta(value: Any) -> Optional[Tuple[str, str, int]]:
        """Extract (filename, content_type, size_bytes) from UploadFile, dict, or file path."""
        import os

        if value is None:
            return None
        # Starlette UploadFile or compatible object
        if hasattr(value, "filename"):
            filename = getattr(value, "filename", "") or ""
            content_type = getattr(value, "content_type", "") or ""
            size = getattr(value, "size", None)
            if size is None and hasattr(value, "file"):
                f = value.file
                if hasattr(f, "tell") and hasattr(f, "seek"):
                    try:
                        cur = f.tell()
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        f.seek(cur)
                    except Exception:
                        size = 0
            return filename, content_type.lower(), int(size or 0)
        # Dict representation
        if isinstance(value, dict) and "filename" in value:
            return str(value["filename"]), str(value.get("content_type", "")).lower(), int(value.get("size", 0))
        # Local file path string
        if isinstance(value, str) and value.strip():
            import mimetypes

            mime, _ = mimetypes.guess_type(value)
            size = os.path.getsize(value) if os.path.exists(value) else 0
            return os.path.basename(value), (mime or "").lower(), size
        return None

    def _rule_file(self, field: str, value: Any, args: List[str]) -> None:
        meta = self._extract_file_meta(value)
        if meta is None or not meta[0]:
            self._add_error(field, "file")

    def _rule_image(self, field: str, value: Any, args: List[str]) -> None:
        meta = self._extract_file_meta(value)
        if meta is None or not meta[0]:
            self._add_error(field, "image")
            return
        filename, content_type, _ = meta
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if not (content_type.startswith("image/") or ext in IMAGE_EXTENSIONS):
            self._add_error(field, "image", code="image_type", types=', '.join(sorted(IMAGE_EXTENSIONS)))

    def _rule_mimes(self, field: str, value: Any, args: List[str]) -> None:
        meta = self._extract_file_meta(value)
        if meta is None or not meta[0] or not args:
            self._add_error(field, "mimes", values=', '.join(args))
            return
        filename, content_type, _ = meta
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = {a.lower().lstrip(".") for a in args}
        matches = ext in allowed or any(content_type == a or content_type.endswith("/" + a) for a in allowed)
        if not matches:
            self._add_error(field, "mimes", values=', '.join(args))

    def _rule_max_file_size(self, field: str, value: Any, args: List[str]) -> None:
        meta = self._extract_file_meta(value)
        if meta is None or not args:
            return
        _, _, size_bytes = meta
        max_kb = float(args[0])
        if (size_bytes / 1024.0) > max_kb:
            self._add_error(field, "max_file_size", value=args[0])

    def _rule_min_file_size(self, field: str, value: Any, args: List[str]) -> None:
        meta = self._extract_file_meta(value)
        if meta is None or not args:
            return
        _, _, size_bytes = meta
        min_kb = float(args[0])
        if (size_bytes / 1024.0) < min_kb:
            self._add_error(field, "min_file_size", value=args[0])

    # -- size ------------------------------------------------------------------

    @staticmethod
    def _size_of(value: Any) -> float:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, (str, list, tuple, dict)):
            return len(value)
        return 0

    def _size_for(self, field: str, value: Any) -> float:
        """Size of a value for min/max/between/size.

        HTML form input arrives as strings; when the field is declared
        `integer`/`numeric`, "25" must compare as the number 25, not as a
        2-character string.
        """
        if isinstance(value, str):
            names = {self._split(r)[0] for r in self._normalise(self.rules.get(field, []))}
            if names & {"integer", "numeric"}:
                try:
                    return float(value)
                except ValueError:
                    pass
        return self._size_of(value)

    def _rule_min(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_for(field, value) < float(args[0]):
            self._add_error(field, "min", value=args[0])

    def _rule_max(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_for(field, value) > float(args[0]):
            self._add_error(field, "max", value=args[0])

    def _rule_between(self, field: str, value: Any, args: List[str]) -> None:
        if len(args) >= 2:
            size = self._size_for(field, value)
            if size < float(args[0]) or size > float(args[1]):
                self._add_error(field, "between", min=args[0], max=args[1])

    def _rule_size(self, field: str, value: Any, args: List[str]) -> None:
        if args and self._size_for(field, value) != float(args[0]):
            self._add_error(field, "size", value=args[0])

    # -- sets and comparisons --------------------------------------------------

    def _rule_in(self, field: str, value: Any, args: List[str]) -> None:
        if str(value) not in args:
            self._add_error(field, "in", values=', '.join(args))

    def _rule_not_in(self, field: str, value: Any, args: List[str]) -> None:
        if str(value) in args:
            self._add_error(field, "not_in", values=', '.join(args))

    def _rule_same(self, field: str, value: Any, args: List[str]) -> None:
        if args and value != self.data.get(args[0]):
            self._add_error(field, "same", value=args[0])

    def _rule_different(self, field: str, value: Any, args: List[str]) -> None:
        if args and value == self.data.get(args[0]):
            self._add_error(field, "different", value=args[0])

    def _rule_confirmed(self, field: str, value: Any, args: List[str]) -> None:
        if value != self.data.get(f"{field}_confirmation"):
            self._add_error(field, "confirmed")

    def _rule_accepted(self, field: str, value: Any, args: List[str]) -> None:
        if value not in (True, 1, "1", "on", "yes", "true"):
            self._add_error(field, "accepted")

    # -- database --------------------------------------------------------------

    def _db(self) -> Any:
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def _database(self) -> Any:
        """The database binding, or None when no application is booted.

        `unique` and `exists` used to wrap the whole query in
        `except Exception: return`, which made the rule *pass* on any database
        error — a typo in the table name, an incompatible column type, a
        connection blip. `unique:userz,email` validated cleanly and the
        duplicate went in. Only the "no database at all" case may be tolerated;
        an actual query failure must surface.
        """
        try:
            from engine.container.application import Container

            return Container.getInstance().make("db")
        except Exception:
            return None

    def _rule_unique(self, field: str, value: Any, args: List[str]) -> None:
        """unique:table[,column[,ignore_id[,id_column]]]"""
        if not args:
            return
        table = _assert_identifier(args[0])
        column = _assert_identifier(args[1] if len(args) > 1 else field)
        query = f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = ?"
        params: List[Any] = [value]

        if len(args) > 2 and args[2] not in ("", "null", "NULL"):
            id_column = _assert_identifier(args[3] if len(args) > 3 else "id")
            query += f" AND {id_column} <> ?"
            params.append(args[2])

        db = self._database()
        if db is None:
            return  # no application booted — skip rather than reject valid data

        row = db.statement(query, params, read=True).fetchone()
        if row is not None and int(row["total"]) > 0:
            self._add_error(field, "unique")

    def _rule_exists(self, field: str, value: Any, args: List[str]) -> None:
        """exists:table[,column]"""
        if not args:
            return
        table = _assert_identifier(args[0])
        column = _assert_identifier(args[1] if len(args) > 1 else field)

        db = self._database()
        if db is None:
            return

        row = db.statement(
            f"SELECT COUNT(*) AS total FROM {table} WHERE {column} = ?",
            [value],
            read=True,
        ).fetchone()
        if row is None or int(row["total"]) == 0:
            self._add_error(field, "exists")

    # -- results ---------------------------------------------------------------

    def passes(self) -> bool:
        return len(self.errors) == 0

    def fails(self) -> bool:
        return not self.passes()

    def validated(self) -> Dict[str, Any]:
        """The validated subset of the input. Raises when validation failed."""
        if self.fails():
            from engine.exceptions.handler import ValidationException

            raise ValidationException(self.errors.to_dict())
        return {k: self.data[k] for k in self.rules if k in self.data}

    def validate(self) -> Dict[str, Any]:
        return self.validated()

    def error_bag(self) -> MessageBag:
        """Return the errors encapsulated in a MessageBag."""
        return self.errors

    def first_error(self, field: Optional[str] = None) -> Optional[str]:
        if field is not None:
            messages = self.errors.get(field)
            return messages[0] if messages else None
        for messages in self.errors.values():
            if messages:
                return messages[0]
        return None

    def error_messages(self) -> List[str]:
        return [message for messages in self.errors.values() for message in messages]


__all__ = ["Validator", "MessageBag", "ViewErrorBag"]

#!/usr/bin/env python3
"""Language standard gate — English-only code, zero hardcoded user-facing strings.

Stack-agnostic enforcement of `LANGUAGE_AND_I18N_STANDARD.md`. Prose does not stop
drift; a non-zero exit code does.

The tool ships zero project knowledge. Everything — roots, source language of the
team, translator function names, key format, exempt paths — comes from
`language-standard.toml` (or `[tool.language_standard]` in `pyproject.toml`).
Without a config file it falls back to conservative defaults.

Rules
-----
LANG-A  Non-ASCII characters in identifiers, comments or docstrings.
LANG-B  Team-language tokens in identifiers, file names, comments or docstrings.
LANG-C  Hardcoded user-facing text that should be a translation key.
LANG-D  Translation key that does not match the canonical format.
LANG-E  File could not be parsed.
LANG-F  Team-language prose in a committed document (Markdown, reST, plain text).

Usage
-----
    python lint_language.py                     # scan roots from config
    python lint_language.py src/ tests/         # scan explicit paths
    python lint_language.py --format github     # CI annotations
    python lint_language.py --strict-strings    # flag every sentence literal
    python lint_language.py --init              # write a starter config file

Exit codes: 0 clean, 1 violations found, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - older runtimes
    tomllib = None  # type: ignore[assignment]

CONFIG_FILENAMES: tuple[str, ...] = ("language-standard.toml", "pyproject.toml")

# --------------------------------------------------------------------------- #
# Built-in token lists — the words a team's own language leaks into identifiers.
# Extend per project through `[tokens] extra_denylist`, never by editing this file.
# --------------------------------------------------------------------------- #

BUILTIN_DENYLISTS: dict[str, frozenset[str]] = {
    "pt": frozenset(
        {
            # people and access
            "usuario", "usuarios", "senha", "senhas", "acesso", "permissao", "perfil",
            "cliente", "clientes", "funcionario", "empresa", "fornecedor", "vendedor",
            # money and commerce
            "saldo", "valor", "valores", "preco", "precos", "desconto", "pagamento",
            "cobranca", "fatura", "boleto", "parcela", "parcelas", "taxa", "taxas",
            "deposito", "saque", "carteira", "extrato", "lancamento", "lancamentos",
            "estorno", "reembolso", "compra", "venda", "vendas", "pedido", "pedidos",
            "produto", "produtos", "servico", "servicos", "contrato", "contratos",
            # generic entities
            "nome", "sobrenome", "endereco", "cidade", "estado", "pais", "bairro",
            "telefone", "celular", "email_usuario", "documento", "documentos",
            "arquivo", "arquivos", "pasta", "imagem", "imagens", "anexo", "anexos",
            "relatorio", "relatorios", "cadastro", "cadastros", "conta", "contas",
            "mensagem", "mensagens", "erro", "erros", "aviso", "sucesso", "falha",
            "quantidade", "descricao", "codigo", "tipo", "situacao", "observacao",
            "historico", "registro", "registros", "item", "itens", "lista", "listas",
            # time
            "data", "hora", "inicio", "fim", "prazo", "vencimento", "duracao",
            "criado", "atualizado", "excluido", "removido", "ativo", "inativo",
            # verbs
            "buscar", "salvar", "excluir", "apagar", "atualizar", "criar", "listar",
            "validar", "calcular", "enviar", "receber", "processar", "verificar",
            "consultar", "gerar", "obter", "definir", "adicionar", "remover",
            "cancelar", "confirmar", "aprovar", "rejeitar", "carregar", "exibir",
            # abbreviations
            "qtd", "vlr", "dt", "cod", "desc", "obs", "num", "ender", "tel", "cad",
        }
    ),
    "es": frozenset(
        {
            "usuario", "usuarios", "contrasena", "clave", "cliente", "clientes",
            "saldo", "valor", "precio", "pago", "factura", "pedido", "producto",
            "nombre", "apellido", "direccion", "ciudad", "estado", "pais", "telefono",
            "mensaje", "mensajes", "error", "errores", "aviso", "exito", "fallo",
            "cantidad", "descripcion", "codigo", "tipo", "fecha", "hora", "inicio",
            "buscar", "guardar", "eliminar", "actualizar", "crear", "listar",
            "validar", "calcular", "enviar", "recibir", "procesar", "verificar",
        }
    ),
    "fr": frozenset(
        {
            "utilisateur", "utilisateurs", "motdepasse", "client", "clients", "solde",
            "valeur", "prix", "paiement", "facture", "commande", "produit", "nom",
            "prenom", "adresse", "ville", "pays", "telephone", "message", "messages",
            "erreur", "erreurs", "quantite", "description", "code", "date", "heure",
            "chercher", "enregistrer", "supprimer", "creer", "valider", "envoyer",
        }
    ),
    "it": frozenset(
        {
            "utente", "utenti", "password_it", "cliente", "clienti", "saldo", "valore",
            "prezzo", "pagamento", "fattura", "ordine", "prodotto", "nome", "cognome",
            "indirizzo", "citta", "paese", "telefono", "messaggio", "errore", "errori",
            "quantita", "descrizione", "codice", "data", "ora", "cercare", "salvare",
            "eliminare", "creare", "validare", "inviare",
        }
    ),
    "de": frozenset(
        {
            "benutzer", "kennwort", "kunde", "kunden", "saldo", "wert", "preis",
            "zahlung", "rechnung", "bestellung", "produkt", "name", "adresse", "stadt",
            "land", "telefon", "nachricht", "fehler", "menge", "beschreibung",
            "datum", "uhrzeit", "suchen", "speichern", "loeschen", "erstellen",
        }
    ),
}

# Function words that carry a language and almost never appear in English text.
# Identifier denylists are useless on prose — `data` and `item` are English too —
# so committed documents are judged by these markers instead.
BUILTIN_PROSE_MARKERS: dict[str, frozenset[str]] = {
    "pt": frozenset(
        {
            "nao", "sao", "esta", "estao", "voce", "voces", "tambem", "porque",
            "entao", "isso", "aquilo", "uma", "umas", "uns", "dos", "das", "pelo",
            "pela", "pelos", "pelas", "nas", "aos", "que", "para", "por", "como",
            "mais", "mas", "ser", "foi", "sera", "sua", "seu", "suas", "seus",
            "onde", "quando", "cada", "ainda", "apenas", "sem", "entre", "depois",
            "quem", "muito", "pode", "deve", "fazer", "feito", "sobre", "qual",
            "quais", "sempre", "nunca", "aqui", "assim", "outro", "outra",
        }
    ),
    "es": frozenset(
        {
            "que", "para", "por", "como", "pero", "sino", "esta", "estan", "una",
            "unas", "unos", "los", "las", "del", "cuando", "donde", "cada", "sin",
            "entre", "despues", "quien", "mucho", "puede", "debe", "hacer", "sobre",
            "siempre", "nunca", "aqui", "asi", "otro", "otra", "tambien", "porque",
        }
    ),
    "fr": frozenset(
        {
            "pas", "sont", "vous", "aussi", "parce", "alors", "cela", "une", "des",
            "les", "pour", "par", "comme", "mais", "etre", "etait", "sera", "son",
            "leur", "quand", "chaque", "encore", "sans", "entre", "apres", "qui",
            "beaucoup", "peut", "doit", "faire", "toujours", "jamais", "ici",
        }
    ),
    "it": frozenset(
        {
            "non", "sono", "anche", "perche", "allora", "questo", "questa", "una",
            "dei", "delle", "degli", "per", "come", "essere", "quando", "dove",
            "ogni", "ancora", "senza", "tra", "dopo", "chi", "molto", "puo",
            "deve", "fare", "sempre", "mai", "qui", "cosi",
        }
    ),
    "de": frozenset(
        {
            "nicht", "sind", "auch", "weil", "dann", "dies", "eine", "einen",
            "einem", "der", "die", "das", "fuer", "durch", "aber", "sein", "war",
            "wird", "wenn", "wann", "jede", "jeden", "noch", "ohne", "zwischen",
            "nach", "wer", "viel", "kann", "muss", "machen", "immer", "nie",
        }
    ),
}

DEFAULT_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "vendor",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build",
    "target", "coverage", ".next", ".nuxt", "storage", "public/build",
)

DEFAULT_PYTHON_GLOBS: tuple[str, ...] = ("*.py",)

DEFAULT_GENERIC_GLOBS: tuple[str, ...] = (
    "*.php", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.kt", "*.rb",
    "*.cs", "*.swift", "*.rs", "*.sql", "*.graphql",
)

DEFAULT_TEMPLATE_GLOBS: tuple[str, ...] = (
    "*.html", "*.htm", "*.vue", "*.svelte", "*.blade.php", "*.twig", "*.jinja",
    "*.jinja2", "*.j2", "*.erb", "*.hbs",
)

# Committed documents are artifacts too: a report, a README or an ADR ships with
# the repository and is read by contributors who do not speak the team language.
DEFAULT_DOC_GLOBS: tuple[str, ...] = (
    "*.md", "*.markdown", "*.mdx", "*.rst", "*.txt", "*.adoc",
)

# Paths that legitimately contain localized copy and are exempt from LANG-A/B/C.
DEFAULT_EXEMPT_GLOBS: tuple[str, ...] = (
    "*/lang/*", "*/locales/*", "*/translations/*", "*/i18n/*",
    "*translation*seed*", "*locale*seed*", "*.po", "*.pot",
)

DEFAULT_TRANSLATOR_FUNCTIONS: tuple[str, ...] = (
    "t", "trans", "translate", "__", "gettext", "ngettext", "tr", "localize",
)

DEFAULT_COPY_SINKS: tuple[str, ...] = (
    "render", "render_template", "view", "template", "flash", "notify", "alert",
    "toast", "abort", "fail", "respond", "json_response", "send_mail", "send_email",
    "send_sms", "send_push", "add_error", "set_message", "with_message", "message",
)

DEFAULT_MESSAGE_KEYS: tuple[str, ...] = (
    "message", "msg", "title", "label", "description", "text", "subject",
    "placeholder", "tooltip", "heading", "caption", "error_message",
)

DEFAULT_KEY_PATTERN = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"

TECHNICAL_STRING_RE = re.compile(
    r"^(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|GRANT|https?://|\w+://"
    r"|/|\./|\.\./|\{|\[|<|%|@|\$|#|[A-Z][A-Z0-9_]{2,}$|\w+/\w+|\w+\.\w{1,4}$)",
    re.IGNORECASE,
)

# Escape hatch for a document that must quote the team language — a standard
# showing a rejected example, an ADR citing a stakeholder verbatim.
IGNORE_FILE_RE = re.compile(r"lint-language:\s*ignore-file")
IGNORE_LINE_RE = re.compile(r"lint-language:\s*ignore\b")

SEGMENT_SPLIT_RE = re.compile(r"[^A-Za-z]+|(?<=[a-z0-9])(?=[A-Z])")
STRING_LITERAL_RE = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`")
TEMPLATE_TEXT_RE = re.compile(r">([^<>{}]{8,})<")
WORD_RE = re.compile(r"[A-Za-z_\u00C0-\u024F]+")


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class Config:
    """Everything project-specific lives here, nothing in the code above."""

    roots: list[str] = field(default_factory=lambda: ["."])
    excluded_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_DIRS))
    exempt_globs: list[str] = field(default_factory=lambda: list(DEFAULT_EXEMPT_GLOBS))
    python_globs: list[str] = field(default_factory=lambda: list(DEFAULT_PYTHON_GLOBS))
    generic_globs: list[str] = field(default_factory=lambda: list(DEFAULT_GENERIC_GLOBS))
    template_globs: list[str] = field(default_factory=lambda: list(DEFAULT_TEMPLATE_GLOBS))
    doc_globs: list[str] = field(default_factory=lambda: list(DEFAULT_DOC_GLOBS))
    denylist: set[str] = field(default_factory=set)
    allowlist: set[str] = field(default_factory=set)
    prose_markers: set[str] = field(default_factory=set)
    translator_functions: set[str] = field(default_factory=lambda: set(DEFAULT_TRANSLATOR_FUNCTIONS))
    copy_sinks: set[str] = field(default_factory=lambda: set(DEFAULT_COPY_SINKS))
    message_keys: set[str] = field(default_factory=lambda: set(DEFAULT_MESSAGE_KEYS))
    key_pattern: re.Pattern[str] = field(default_factory=lambda: re.compile(DEFAULT_KEY_PATTERN))
    min_words: int = 3
    min_chars: int = 8
    strict_strings: bool = False
    check_templates: bool = True
    check_docs: bool = True
    min_prose_markers: int = 4

    @classmethod
    def load(cls, explicit: Path | None = None) -> "Config":
        """Read configuration from TOML, falling back to defaults."""
        raw = _read_config_table(explicit)
        config = cls()

        config.roots = list(raw.get("roots", config.roots))
        config.excluded_dirs |= set(raw.get("exclude_dirs", ()))
        config.exempt_globs += list(raw.get("exempt_globs", ()))
        config.strict_strings = bool(raw.get("strict_strings", config.strict_strings))
        config.check_templates = bool(raw.get("check_templates", config.check_templates))
        config.check_docs = bool(raw.get("check_docs", config.check_docs))
        config.min_prose_markers = int(raw.get("min_prose_markers", config.min_prose_markers))

        files = raw.get("files", {})
        config.python_globs = list(files.get("python", config.python_globs))
        config.generic_globs = list(files.get("generic", config.generic_globs))
        config.template_globs = list(files.get("templates", config.template_globs))
        config.doc_globs = list(files.get("docs", config.doc_globs))

        tokens = raw.get("tokens", {})
        locales = [str(locale).lower() for locale in tokens.get("denylist_locales", ["pt"])]
        for locale in locales:
            config.denylist |= BUILTIN_DENYLISTS.get(locale, frozenset())
            config.prose_markers |= BUILTIN_PROSE_MARKERS.get(locale, frozenset())
        config.denylist |= {str(word).lower() for word in tokens.get("extra_denylist", ())}
        config.allowlist |= {str(word).lower() for word in tokens.get("allowlist", ())}
        config.denylist -= config.allowlist
        config.prose_markers |= {
            str(word).lower() for word in tokens.get("extra_prose_markers", ())
        }
        config.prose_markers -= config.allowlist

        i18n = raw.get("i18n", {})
        config.translator_functions |= {str(name) for name in i18n.get("translator_functions", ())}
        if "key_pattern" in i18n:
            config.key_pattern = re.compile(str(i18n["key_pattern"]))

        copy = raw.get("copy", {})
        config.copy_sinks |= {str(name) for name in copy.get("sinks", ())}
        config.message_keys |= {str(name) for name in copy.get("message_keys", ())}
        config.min_words = int(copy.get("min_words", config.min_words))
        config.min_chars = int(copy.get("min_chars", config.min_chars))

        if not config.denylist:
            config.denylist = set(BUILTIN_DENYLISTS["pt"])
        if not config.prose_markers:
            config.prose_markers = set(BUILTIN_PROSE_MARKERS["pt"])
        return config

    def is_exempt(self, path: Path) -> bool:
        """True when the path legitimately holds localized copy."""
        posix = path.as_posix()
        return any(Path(posix).match(pattern) for pattern in self.exempt_globs)

    def forbidden_tokens_in(self, name: str) -> list[str]:
        """Return the team-language segments found inside an identifier."""
        segments = _split_identifier(_strip_accents(name))
        return [
            segment
            for segment in segments
            if segment in self.denylist and segment not in self.allowlist
        ]

    def looks_like_sentence(self, value: str) -> bool:
        """True when a literal reads as human copy rather than a technical token."""
        stripped = value.strip().strip("\"'`")
        if len(stripped) < self.min_chars or TECHNICAL_STRING_RE.match(stripped):
            return False
        if self.key_pattern.match(stripped):
            return False
        return len(stripped.split()) >= self.min_words


def _read_config_table(explicit: Path | None) -> dict:
    """Locate and parse the `[language_standard]` table, or return an empty one."""
    candidates = [explicit] if explicit else [Path(name) for name in CONFIG_FILENAMES]
    for candidate in candidates:
        if candidate is None or not candidate.exists() or tomllib is None:
            continue
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        if candidate.name == "pyproject.toml":
            table = data.get("tool", {}).get("language_standard")
        else:
            table = data.get("language_standard", data)
        if table:
            return table
    return {}


# --------------------------------------------------------------------------- #
# Result model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Violation:
    """A single breach, addressable by file and line."""

    path: Path
    line: int
    column: int
    rule: str
    detail: str

    def render(self, style: str) -> str:
        if style == "github":
            return (
                f"::error file={self.path},line={self.line},col={self.column},"
                f"title={self.rule}::{self.detail}"
            )
        return f"{self.path}:{self.line}:{self.column}: {self.rule} {self.detail}"


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #


def _split_identifier(name: str) -> list[str]:
    """Split `getUserSaldo`, `saldo_maximo` and `SALDO` into lowercase segments."""
    return [segment.lower() for segment in SEGMENT_SPLIT_RE.split(name) if segment]


def _strip_accents(value: str) -> str:
    """Remove diacritics so `endereço` matches the ASCII denylist entry."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens_in_text(text: str, config: Config) -> list[str]:
    """Return forbidden tokens found in free text (comments, docstrings)."""
    found: set[str] = set()
    for word in WORD_RE.findall(text):
        found.update(config.forbidden_tokens_in(word))
    return sorted(found)


def iter_files(roots: Sequence[Path], globs: Iterable[str], config: Config) -> Iterator[Path]:
    """Yield files under `roots` matching `globs`, skipping excluded directories."""
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            if any(root.match(pattern) for pattern in globs) and root not in seen:
                seen.add(root)
                yield root
            continue
        for pattern in globs:
            for path in root.rglob(pattern):
                if path in seen or not config.excluded_dirs.isdisjoint(path.parts):
                    continue
                seen.add(path)
                yield path


# --------------------------------------------------------------------------- #
# Python analysis (AST-accurate)
# --------------------------------------------------------------------------- #


class PythonVisitor(ast.NodeVisitor):
    """Collect LANG-B, LANG-C and LANG-D violations from a Python module."""

    def __init__(self, path: Path, config: Config) -> None:
        self.path = path
        self.config = config
        self.violations: list[Violation] = []

    def _check_name(self, name: str, node: ast.AST, kind: str) -> None:
        tokens = self.config.forbidden_tokens_in(name)
        if tokens:
            self.violations.append(
                Violation(
                    self.path,
                    getattr(node, "lineno", 1),
                    getattr(node, "col_offset", 0) + 1,
                    "LANG-B",
                    f"non-English {kind} '{name}' (tokens: {', '.join(tokens)})",
                )
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._check_name(node.name, node, "function")
        self.generic_visit(node)  # parameters are reached through visit_arg

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._check_name(node.name, node, "class")
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:  # noqa: N802
        self._check_name(node.arg, node, "parameter")

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self._check_name(node.id, node, "variable")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self._check_name(node.attr, node, "attribute")
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:  # noqa: N802
        if isinstance(node.exc, ast.Call):
            for argument in node.exc.args:
                self._flag_if_sentence(argument, "raised exception message")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        target = self._call_name(node.func)
        if target in self.config.copy_sinks:
            for argument in node.args:
                self._flag_if_sentence(argument, f"argument to '{target}()'")
            for keyword in node.keywords:
                if keyword.arg and keyword.arg.lower() in self.config.message_keys:
                    self._flag_if_sentence(keyword.value, f"'{keyword.arg}=' in '{target}()'")
        if target in self.config.translator_functions and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if not self.config.key_pattern.match(first.value):
                    self.violations.append(
                        Violation(
                            self.path,
                            first.lineno,
                            first.col_offset + 1,
                            "LANG-D",
                            f'invalid translation key "{first.value[:48]}" — expected '
                            f"canonical dot.case key, not literal copy",
                        )
                    )
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:  # noqa: N802
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if key.value.lower() in self.config.message_keys:
                    self._flag_if_sentence(value, f"dict key '{key.value}'")
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802
        literal = "".join(
            part.value for part in node.values if isinstance(part, ast.Constant)
        ).strip()
        if literal and self.config.looks_like_sentence(literal):
            self.violations.append(
                Violation(
                    self.path,
                    node.lineno,
                    node.col_offset + 1,
                    "LANG-C",
                    "interpolated string builds a sentence; use one translation key "
                    "with named ICU placeholders",
                )
            )
        self.generic_visit(node)

    def _flag_if_sentence(self, node: ast.AST, context: str) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if self.config.looks_like_sentence(node.value):
                self.violations.append(
                    Violation(
                        self.path,
                        node.lineno,
                        node.col_offset + 1,
                        "LANG-C",
                        f'hardcoded user-facing text in {context}: "{node.value.strip()[:48]}" '
                        f"— replace with a translation key",
                    )
                )

    @staticmethod
    def _call_name(func: ast.AST) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""


def analyze_python(path: Path, config: Config) -> list[Violation]:
    """Run every check against one Python file."""
    source = path.read_text(encoding="utf-8")
    violations = check_file_name(path, config)
    if not config.is_exempt(path):
        violations += _check_python_tokens(path, source, config)

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return [*violations, Violation(path, error.lineno or 1, 1, "LANG-E", f"parse error: {error.msg}")]

    if not config.is_exempt(path):
        violations += _check_python_docstrings(tree, path, config)
        visitor = PythonVisitor(path, config)
        visitor.visit(tree)
        violations += visitor.violations
    return violations


def _check_python_tokens(path: Path, source: str, config: Config) -> list[Violation]:
    """Flag non-ASCII identifiers and team-language comments."""
    violations: list[Violation] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return violations

    for token in tokens:
        if token.type == tokenize.COMMENT:
            if any(ord(char) > 127 for char in token.string):
                violations.append(
                    Violation(path, token.start[0], token.start[1] + 1, "LANG-A",
                              "non-ASCII characters in a comment — comments are English")
                )
                continue
            found = _tokens_in_text(token.string, config)
            if found:
                violations.append(
                    Violation(path, token.start[0], token.start[1] + 1, "LANG-B",
                              f"non-English comment (tokens: {', '.join(found)})")
                )
        elif token.type == tokenize.NAME and any(ord(char) > 127 for char in token.string):
            violations.append(
                Violation(path, token.start[0], token.start[1] + 1, "LANG-A",
                          f"non-ASCII identifier '{token.string}'")
            )
    return violations


def _check_python_docstrings(tree: ast.AST, path: Path, config: Config) -> list[Violation]:
    """Flag docstrings written in the team's language instead of English."""
    violations: list[Violation] = []
    targets = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, targets):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        line = getattr(node, "lineno", 1)
        if any(ord(char) > 127 for char in docstring):
            violations.append(
                Violation(path, line, 1, "LANG-A",
                          "non-ASCII docstring — docstrings are technical English")
            )
            continue
        found = _tokens_in_text(docstring, config)
        if found:
            violations.append(
                Violation(path, line, 1, "LANG-B",
                          f"non-English docstring (tokens: {', '.join(found)})")
            )
    return violations


# --------------------------------------------------------------------------- #
# Generic analysis (any other language, line-based)
# --------------------------------------------------------------------------- #


def analyze_generic(path: Path, config: Config, is_template: bool = False) -> list[Violation]:
    """Scan a non-Python source file for the same four rules, line by line."""
    violations = check_file_name(path, config)
    if config.is_exempt(path):
        return violations

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return violations

    sink_pattern = _sink_pattern(config)
    translator_pattern = _translator_pattern(config)

    for number, line in enumerate(lines, 1):
        literals = [(match.group(0), match.start()) for match in STRING_LITERAL_RE.finditer(line)]
        skeleton = STRING_LITERAL_RE.sub(lambda match: " " * len(match.group(0)), line)

        found = _tokens_in_text(skeleton, config)
        if found:
            violations.append(
                Violation(path, number, 1, "LANG-B",
                          f"non-English identifier or comment (tokens: {', '.join(found)})")
            )
        elif any(ord(char) > 127 for char in skeleton):
            violations.append(
                Violation(path, number, 1, "LANG-A",
                          "non-ASCII characters outside a string literal")
            )

        for literal, offset in literals:
            body = literal[1:-1]
            if translator_pattern and translator_pattern.search(line):
                match = translator_pattern.search(line)
                if match and match.group(1) and not config.key_pattern.match(match.group(1)):
                    violations.append(
                        Violation(path, number, offset + 1, "LANG-D",
                                  f'invalid translation key "{match.group(1)[:48]}" — expected '
                                  f"canonical dot.case key")
                    )
                    break
            if not config.looks_like_sentence(body):
                continue
            if config.strict_strings or (sink_pattern and sink_pattern.search(line)):
                violations.append(
                    Violation(path, number, offset + 1, "LANG-C",
                              f'hardcoded user-facing text: "{body.strip()[:48]}" '
                              f"— replace with a translation key")
                )

        if is_template and config.check_templates:
            for match in TEMPLATE_TEXT_RE.finditer(line):
                text = match.group(1).strip()
                if config.looks_like_sentence(text):
                    violations.append(
                        Violation(path, number, match.start() + 1, "LANG-C",
                                  f'hardcoded text node: "{text[:48]}" '
                                  f"— replace with a translation key")
                    )
    return violations


def analyze_docs(path: Path, config: Config) -> list[Violation]:
    """Flag a committed document written in the team language instead of English.

    Judged over the whole file: one quoted word proves nothing, a paragraph of
    function words does. `lint-language: ignore-file` exempts a document that has
    to quote the team language; `lint-language: ignore` exempts a single line.
    """
    violations = check_file_name(path, config)
    if config.is_exempt(path) or not config.prose_markers:
        return violations

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return violations
    if IGNORE_FILE_RE.search(text):
        return violations

    evidence: dict[str, int] = {}
    first_line = 0
    for number, line in enumerate(text.splitlines(), 1):
        if IGNORE_LINE_RE.search(line):
            continue
        for word in WORD_RE.findall(_strip_accents(line).lower()):
            if word in config.prose_markers:
                evidence[word] = evidence.get(word, 0) + 1
                first_line = first_line or number

    if len(evidence) < config.min_prose_markers:
        return violations

    sample = ", ".join(sorted(evidence, key=lambda word: -evidence[word])[:6])
    violations.append(
        Violation(path, first_line or 1, 1, "LANG-F",
                  f"team-language prose in a committed document "
                  f"({len(evidence)} markers: {sample}) — rewrite it in English")
    )
    return violations


def _sink_pattern(config: Config) -> re.Pattern[str] | None:
    if not config.copy_sinks:
        return None
    names = "|".join(sorted(re.escape(name) for name in config.copy_sinks))
    keys = "|".join(sorted(re.escape(name) for name in config.message_keys))
    # Matches `sink(`, `message:`, `message =`, `'message' =>` and `"message":`.
    return re.compile(
        rf"\b(?:{names})\s*\(|[\"'`]?\b(?:{keys})\b[\"'`]?\s*(?:=>|::|[:=])",
        re.IGNORECASE,
    )


def _translator_pattern(config: Config) -> re.Pattern[str] | None:
    if not config.translator_functions:
        return None
    names = "|".join(sorted(re.escape(name) for name in config.translator_functions))
    return re.compile(rf"\b(?:{names})\s*\(\s*[\"'`]([^\"'`]+)[\"'`]")


def check_file_name(path: Path, config: Config) -> list[Violation]:
    """Flag team-language tokens in module, migration or component file names."""
    stem = path.name.split(".")[0]
    tokens = config.forbidden_tokens_in(stem)
    if not tokens:
        return []
    return [
        Violation(path, 1, 1, "LANG-B",
                  f"non-English file name '{path.name}' (tokens: {', '.join(tokens)})")
    ]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

STARTER_CONFIG = """# Language standard gate — project configuration.
# Everything project-specific belongs here; never edit the linter itself.

[language_standard]
roots = ["src", "app", "tests"]
exclude_dirs = []
exempt_globs = ["*/lang/*", "*/locales/*", "*/translations/*"]
strict_strings = false      # true: every sentence literal is a violation
check_templates = true
check_docs = true           # committed documents must be English prose too
min_prose_markers = 4       # distinct markers before a document is flagged

[language_standard.files]
python    = ["*.py"]
generic   = ["*.php", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.sql"]
templates = ["*.html", "*.vue", "*.blade.php", "*.twig"]
docs      = ["*.md", "*.mdx", "*.rst", "*.txt"]

[language_standard.tokens]
denylist_locales   = ["pt"]  # built-in lists: pt, es, fr, it, de
extra_denylist     = []      # project-specific words that must never appear
extra_prose_markers = []     # extra function words that betray the team language
allowlist          = ["cpf", "cnpj", "pix", "iban"]  # legal or protocol proper nouns

[language_standard.i18n]
key_pattern          = "^[a-z0-9_]+(\\\\.[a-z0-9_]+)+$"
translator_functions = ["t", "trans", "translate", "__"]

[language_standard.copy]
sinks        = []
message_keys = []
min_words    = 3
min_chars    = 8
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Scan the requested paths and return a shell exit code."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="*", help="files or directories (default: config roots)")
    parser.add_argument("--config", type=Path, default=None, help="path to a TOML config file")
    parser.add_argument("--format", choices=("text", "github"), default="text")
    parser.add_argument("--strict-strings", action="store_true", help="flag every sentence literal")
    parser.add_argument("--init", action="store_true", help="write a starter config file and exit")
    arguments = parser.parse_args(argv)

    if arguments.init:
        target = Path("language-standard.toml")
        if target.exists():
            print(f"{target} already exists", file=sys.stderr)
            return 2
        target.write_text(STARTER_CONFIG, encoding="utf-8")
        print(f"Wrote {target}")
        return 0

    if tomllib is None and arguments.config:
        print("lint_language: TOML support requires Python 3.11+", file=sys.stderr)
        return 2

    config = Config.load(arguments.config)
    if arguments.strict_strings:
        config.strict_strings = True

    roots = [Path(item) for item in (arguments.paths or config.roots)]
    roots = [root for root in roots if root.exists()]
    if not roots:
        print("lint_language: no existing path to scan", file=sys.stderr)
        return 2

    violations: list[Violation] = []
    for path in iter_files(roots, config.python_globs, config):
        violations.extend(analyze_python(path, config))
    for path in iter_files(roots, config.generic_globs, config):
        violations.extend(analyze_generic(path, config))
    for path in iter_files(roots, config.template_globs, config):
        violations.extend(analyze_generic(path, config, is_template=True))
    if config.check_docs:
        for path in iter_files(roots, config.doc_globs, config):
            violations.extend(analyze_docs(path, config))

    for violation in sorted(violations, key=lambda item: (str(item.path), item.line, item.column)):
        print(violation.render(arguments.format))

    if violations:
        by_rule: dict[str, int] = {}
        for violation in violations:
            by_rule[violation.rule] = by_rule.get(violation.rule, 0) + 1
        summary = ", ".join(f"{rule}: {count}" for rule, count in sorted(by_rule.items()))
        print(f"\nFAILED — {len(violations)} violation(s) ({summary})", file=sys.stderr)
        return 1

    print("Language standard: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

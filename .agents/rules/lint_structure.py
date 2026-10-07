#!/usr/bin/env python3
"""Structure gate — layer purity and hard size thresholds for Python codebases.

Companion to `lint_language.py`. That gate answers "is this English?"; this one
answers "does this file respect its layer?". Both read the same config file and
both ship zero project knowledge: layers, caps and forbidden artifacts come from
the `[structure_standard]` table of `language-standard.toml` (or
`[tool.structure_standard]` in `pyproject.toml`).

Disabled unless the config turns it on, so adding the gate to a repository is a
deliberate act rather than a surprise on the next edit.

Rules
-----
STRUCT-A  File longer than its layer's cap.
STRUCT-B  Function or method longer than its cap (tighter inside controllers).
STRUCT-C  Cyclomatic complexity above the cap.
STRUCT-D  SQL leaking into a layer that must delegate to a repository.
STRUCT-E  Markup built inside Python instead of a template.
STRUCT-F  Stack artifact the project forbids (TypeScript, Node build pipeline).
STRUCT-G  Broad or bare `except` that swallows what it cannot name.
STRUCT-H  Parameter or return without a type annotation.
STRUCT-I  Public class or function without a docstring.

Usage
-----
    python lint_structure.py                    # scan roots from config
    python lint_structure.py app/ tests/        # scan explicit paths
    python lint_structure.py --format github    # CI annotations

Exit codes: 0 clean, 1 violations found, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - older runtimes
    tomllib = None  # type: ignore[assignment]

CONFIG_FILENAMES: tuple[str, ...] = ("language-standard.toml", "pyproject.toml")

DEFAULT_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "vendor",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build",
    "target", "coverage", ".next", ".nuxt", "storage", "migrations",
)

# Layer names as they appear in a path, singular or plural, any capitalization:
# `app/Http/Controllers/`, `app/modules/billing/controllers/` both match.
DEFAULT_LAYERS: tuple[dict[str, object], ...] = (
    {
        "name": "controller",
        "pattern": r"(^|/)controllers?(/|$)",
        "max_file_lines": 150,
        "max_function_lines": 15,
        "no_sql": True,
        "no_markup": True,
    },
    {
        "name": "service",
        "pattern": r"(^|/)services?(/|$)",
        "max_file_lines": 300,
        "no_sql": True,
        "no_markup": True,
    },
    {
        "name": "repository",
        "pattern": r"(^|/)repositor(y|ies)(/|$)",
        "max_file_lines": 250,
        "no_markup": True,
    },
)

SQL_RE = re.compile(
    r"\b(?:SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM"
    r"|(?:INNER|LEFT|RIGHT|FULL|CROSS)\s+JOIN|GROUP\s+BY|ORDER\s+BY\s+\w)\b",
    re.IGNORECASE | re.DOTALL,
)

MARKUP_RE = re.compile(
    r"<\s*/?\s*(?:html|head|body|div|span|table|thead|tbody|tr|td|th|ul|ol|li"
    r"|form|input|select|option|button|section|header|footer|nav|article|aside"
    r"|h[1-6]|p|a|img|script|style|label|textarea)\b",
    re.IGNORECASE,
)

# Nodes that add one path through a function.
BRANCH_NODES: tuple[type[ast.AST], ...] = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
    ast.IfExp, ast.Assert, ast.comprehension,
)

# Catching these names catches everything, which is the same as not knowing what
# went wrong. Name the exception you can actually handle.
BROAD_EXCEPTIONS: frozenset[str] = frozenset({"Exception", "BaseException"})

# Receivers that carry no annotation by convention.
IMPLICIT_ARGS: frozenset[str] = frozenset({"self", "cls"})


@dataclass(slots=True)
class Layer:
    """One architectural layer and the limits it answers to."""

    name: str
    pattern: re.Pattern[str]
    max_file_lines: int
    max_function_lines: int | None = None
    no_sql: bool = False
    no_markup: bool = False


@dataclass(slots=True)
class Config:
    """Everything project-specific lives here, nothing in the code above."""

    enabled: bool = False
    roots: list[str] = field(default_factory=lambda: ["."])
    excluded_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_DIRS))
    exempt_globs: list[str] = field(default_factory=list)
    python_globs: list[str] = field(default_factory=lambda: ["*.py"])
    layers: list[Layer] = field(default_factory=list)
    default_max_file_lines: int = 0
    max_function_lines: int = 25
    max_complexity: int = 6
    forbidden_globs: list[str] = field(default_factory=list)
    require_type_hints: bool = True
    require_docstrings: bool = True
    forbid_broad_except: bool = True

    @classmethod
    def load(cls, explicit: Path | None = None) -> "Config":
        """Read configuration from TOML, falling back to the built-in defaults."""
        raw = _read_config_table(explicit)
        config = cls()

        config.enabled = bool(raw.get("enabled", config.enabled))
        config.roots = list(raw.get("roots", config.roots))
        config.excluded_dirs |= set(raw.get("exclude_dirs", ()))
        config.exempt_globs += list(raw.get("exempt_globs", ()))
        config.python_globs = list(raw.get("python_globs", config.python_globs))
        config.default_max_file_lines = int(
            raw.get("default_max_file_lines", config.default_max_file_lines)
        )
        config.max_function_lines = int(
            raw.get("max_function_lines", config.max_function_lines)
        )
        config.max_complexity = int(raw.get("max_complexity", config.max_complexity))
        config.forbidden_globs = list(raw.get("forbidden_globs", ()))
        config.require_type_hints = bool(
            raw.get("require_type_hints", config.require_type_hints)
        )
        config.require_docstrings = bool(
            raw.get("require_docstrings", config.require_docstrings)
        )
        config.forbid_broad_except = bool(
            raw.get("forbid_broad_except", config.forbid_broad_except)
        )

        declared = raw.get("layers") or DEFAULT_LAYERS
        for entry in declared:
            config.layers.append(
                Layer(
                    name=str(entry.get("name", "layer")),
                    pattern=re.compile(str(entry["pattern"]), re.IGNORECASE),
                    max_file_lines=int(entry.get("max_file_lines", 0)),
                    max_function_lines=(
                        int(entry["max_function_lines"])
                        if entry.get("max_function_lines")
                        else None
                    ),
                    no_sql=bool(entry.get("no_sql", False)),
                    no_markup=bool(entry.get("no_markup", False)),
                )
            )
        return config

    def layer_for(self, path: Path) -> Layer | None:
        """Return the layer whose pattern claims this path, if any."""
        posix = path.as_posix()
        for layer in self.layers:
            if layer.pattern.search(posix):
                return layer
        return None

    def is_exempt(self, path: Path) -> bool:
        """True when the path is explicitly outside this gate."""
        posix = path.as_posix()
        return any(Path(posix).match(pattern) for pattern in self.exempt_globs)


def _read_config_table(explicit: Path | None) -> dict:
    """Locate `[structure_standard]` in the first config file that declares it."""
    candidates = [explicit] if explicit else [Path(name) for name in CONFIG_FILENAMES]
    for candidate in candidates:
        if candidate is None or not candidate.exists() or tomllib is None:
            continue
        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        if candidate.name == "pyproject.toml":
            table = data.get("tool", {}).get("structure_standard")
        else:
            table = data.get("structure_standard")
        if table:
            return table
    return {}


@dataclass(slots=True, frozen=True)
class Violation:
    """One rejected fact about one line."""

    path: Path
    line: int
    rule: str
    message: str

    def render(self, style: str) -> str:
        """Format for a terminal or for GitHub Actions annotations."""
        if style == "github":
            return (
                f"::error file={self.path},line={self.line}::"
                f"{self.rule} {self.message}"
            )
        return f"{self.path}:{self.line}: {self.rule} {self.message}"


def iter_files(
    roots: Sequence[Path], globs: Iterable[str], config: Config
) -> Iterator[Path]:
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


def _complexity(node: ast.AST) -> int:
    """Cyclomatic complexity: one path plus every branch the body can take."""
    score = 1
    for child in ast.walk(node):
        if isinstance(child, BRANCH_NODES):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.Match):
            score += len(child.cases)
    return score


def _body_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Length of a function body, excluding its signature and decorators."""
    end = node.end_lineno or node.lineno
    start = node.body[0].lineno if node.body else node.lineno
    return end - start + 1


def analyze_python(path: Path, config: Config) -> list[Violation]:
    """Apply the size, complexity and layer-purity rules to one module."""
    if config.is_exempt(path):
        return []

    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    violations: list[Violation] = []
    layer = config.layer_for(path)
    total = len(source.splitlines())

    cap = layer.max_file_lines if layer else config.default_max_file_lines
    label = f"{layer.name} " if layer else ""
    if cap and total > cap:
        violations.append(
            Violation(path, 1, "STRUCT-A",
                      f"{label}file is {total} lines, cap is {cap} — split it into "
                      f"focused units")
        )

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return violations + [
            Violation(path, error.lineno or 1, "STRUCT-A", f"unparseable: {error.msg}")
        ]

    function_cap = (
        layer.max_function_lines
        if layer and layer.max_function_lines
        else config.max_function_lines
    )
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        length = _body_lines(node)
        if length > function_cap:
            violations.append(
                Violation(path, node.lineno, "STRUCT-B",
                          f"{label}'{node.name}' is {length} lines, cap is "
                          f"{function_cap} — extract the steps")
            )
        score = _complexity(node)
        if score > config.max_complexity:
            violations.append(
                Violation(path, node.lineno, "STRUCT-C",
                          f"'{node.name}' has cyclomatic complexity {score}, cap is "
                          f"{config.max_complexity} — flatten the branching")
            )
        if config.require_type_hints:
            violations.extend(_check_annotations(node, path))
        if config.require_docstrings:
            violations.extend(_check_docstring(node, path, "function"))

    if config.require_docstrings:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                violations.extend(_check_docstring(node, path, "class"))

    if config.forbid_broad_except:
        violations.extend(_check_except(tree, path))

    if layer and (layer.no_sql or layer.no_markup):
        violations.extend(_check_literals(tree, path, layer))
    return violations


def _check_annotations(
    node: ast.FunctionDef | ast.AsyncFunctionDef, path: Path
) -> list[Violation]:
    """Require a type on every parameter and on the return."""
    violations: list[Violation] = []
    arguments = node.args
    positional = list(arguments.posonlyargs) + list(arguments.args)
    optional = [arguments.vararg, arguments.kwarg]
    every = positional + list(arguments.kwonlyargs) + [arg for arg in optional if arg]

    for index, argument in enumerate(every):
        if argument.annotation is not None:
            continue
        if index == 0 and argument.arg in IMPLICIT_ARGS:
            continue
        violations.append(
            Violation(path, argument.lineno, "STRUCT-H",
                      f"'{node.name}({argument.arg})' has no type annotation")
        )

    if node.returns is None:
        violations.append(
            Violation(path, node.lineno, "STRUCT-H",
                      f"'{node.name}' has no return type annotation")
        )
    return violations


def _check_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, path: Path, kind: str
) -> list[Violation]:
    """Require a Google-style docstring on everything public."""
    if node.name.startswith("_") or ast.get_docstring(node):
        return []
    return [
        Violation(path, node.lineno, "STRUCT-I",
                  f"public {kind} '{node.name}' has no docstring")
    ]


def _check_except(tree: ast.AST, path: Path) -> list[Violation]:
    """Flag handlers that catch more than they can name."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            caught = "bare except"
        elif isinstance(node.type, ast.Name) and node.type.id in BROAD_EXCEPTIONS:
            caught = f"except {node.type.id}"
        else:
            continue
        violations.append(
            Violation(path, node.lineno, "STRUCT-G",
                      f"{caught} swallows every failure — catch the specific "
                      f"exception you can handle")
        )
    return violations


def _check_literals(tree: ast.AST, path: Path, layer: Layer) -> list[Violation]:
    """Flag SQL and markup embedded in a layer that must delegate them."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = node.value
        if layer.no_sql and SQL_RE.search(value):
            violations.append(
                Violation(path, node.lineno, "STRUCT-D",
                          f"SQL inside a {layer.name} — move the query into a "
                          f"repository")
            )
        elif layer.no_markup and MARKUP_RE.search(value):
            violations.append(
                Violation(path, node.lineno, "STRUCT-E",
                          f"markup inside a {layer.name} — render an .html template "
                          f"instead")
            )
    return violations


def check_forbidden(roots: Sequence[Path], config: Config) -> list[Violation]:
    """Flag files whose mere existence breaks the project's stack boundaries."""
    if not config.forbidden_globs:
        return []
    return [
        Violation(path, 1, "STRUCT-F",
                  "forbidden stack artifact — this project's boundaries exclude it")
        for path in iter_files(roots, config.forbidden_globs, config)
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Scan the requested paths and return a shell exit code."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="*", help="files or directories")
    parser.add_argument("--config", type=Path, default=None, help="path to a TOML config")
    parser.add_argument("--format", choices=("text", "github"), default="text")
    arguments = parser.parse_args(argv)

    if tomllib is None and arguments.config:
        print("lint_structure: TOML support requires Python 3.11+", file=sys.stderr)
        return 2

    config = Config.load(arguments.config)
    if not config.enabled:
        print("Structure standard: disabled for this project.")
        return 0

    roots = [Path(item) for item in (arguments.paths or config.roots)]
    roots = [root for root in roots if root.exists()]
    if not roots:
        print("lint_structure: no existing path to scan", file=sys.stderr)
        return 2

    violations: list[Violation] = []
    for path in iter_files(roots, config.python_globs, config):
        violations.extend(analyze_python(path, config))
    violations.extend(check_forbidden(roots, config))

    for violation in sorted(violations, key=lambda item: (str(item.path), item.line)):
        print(violation.render(arguments.format))

    if violations:
        by_rule: dict[str, int] = {}
        for violation in violations:
            by_rule[violation.rule] = by_rule.get(violation.rule, 0) + 1
        summary = ", ".join(f"{rule}: {count}" for rule, count in sorted(by_rule.items()))
        print(f"\nFAILED — {len(violations)} violation(s) ({summary})", file=sys.stderr)
        return 1

    print("Structure standard: clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

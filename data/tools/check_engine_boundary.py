"""Engine boundary gate: the framework never imports the application.

Business rules belong to the application's modules and plugins. The engine is
extended only through the seams it offers - the internal proxy, events,
plugins and themes - so an engine file importing application code is the
structural sign of a business rule written into the framework.

The check is static (AST only; nothing is imported) and ratcheted: a finding
fails the gate only when it is new against the base commit pinned in
`tools/engine-boundary-policy.json`. Existing debt can shrink, never grow.

Exit codes: 0 clean, 1 new findings, 2 the gate could not run.

    python tools/check_engine_boundary.py           # ratchet against the policy base
    python tools/check_engine_boundary.py --full    # list every finding, debt included
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "tools" / "engine-boundary-policy.json"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DYNAMIC_IMPORTERS = {"import_module", "__import__"}


@dataclass(frozen=True)
class Finding:
    """One forbidden import: where it is and what it reaches."""

    path: str
    line: int
    code: str
    target: str

    def signature(self) -> tuple[str, str, str]:
        """Identity for the ratchet: moving a finding to another line is not new."""
        return (self.path, self.code, self.target)

    def __str__(self) -> str:
        return " ".join((f"{self.path}:{self.line}:", self.code, self.target))


class GateBlocked(Exception):
    """The gate could not run, so it cannot vouch for anything.

    Args:
        code: Machine code naming why the gate could not run.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def imported_modules(tree: ast.AST) -> Iterator[tuple[int, str]]:
    """Yield (line, absolute module) for every import, including literal dynamic ones.

    Relative imports stay inside their own package and are skipped.
    """
    importers = _DYNAMIC_IMPORTERS | _importer_aliases(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from ((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module
        elif isinstance(node, ast.Call):
            target = _literal_dynamic_import(node, importers)
            if target is not None:
                yield node.lineno, target


def _importer_aliases(tree: ast.AST) -> set[str]:
    """Names `import_module` was imported under (`from importlib import import_module as load`)."""
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "importlib"
        for alias in node.names
        if alias.name == "import_module"
    }


def _literal_dynamic_import(node: ast.Call, importers: set[str]) -> Optional[str]:
    """Return the literal module name of a dynamic import call, positional or `name=`."""
    func = node.func
    called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if called not in importers:
        return None
    first = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "name"), None)
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _matches(module: str, prefixes: Iterable[str]) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def _rules_for(path: str, policy: dict) -> list[tuple[str, list[str]]]:
    """Return the (code, forbidden module prefixes) rules that apply to `path`."""
    rules = []
    if any(path.startswith(root.rstrip("/") + "/") for root in policy["engine_roots"]):
        rules.append(("ENGINE_APP_IMPORT", policy["application_packages"]))
    if any(marker in path for marker in policy["service_markers"]):
        rules.append(("SERVICE_CONTROLLER_IMPORT", policy["controller_packages"]))
    return rules


def scan_source(path: str, source: str, policy: dict) -> list[Finding]:
    """Return the boundary findings of one file's source."""
    rules = _rules_for(path, policy)
    if not rules:
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        return [Finding(path, error.lineno or 1, "BOUNDARY_SYNTAX", "unparseable")]
    return [
        Finding(path, line, code, module)
        for line, module in imported_modules(tree)
        for code, forbidden in rules
        if _matches(module, forbidden)
    ]


def scan_tree(root: Path, policy: dict) -> list[Finding]:
    """Scan every Python file under the policy's scan roots.

    Raises:
        GateBlocked: A scan root does not exist - an empty scan proves nothing.
    """
    findings: list[Finding] = []
    for scan_root in policy["scan_roots"]:
        if not (root / scan_root).is_dir():
            raise GateBlocked("BOUNDARY_SCAN_ROOT_MISSING")
        for file in sorted((root / scan_root).rglob("*.py")):
            findings.extend(_scan_file(root, file, policy))
    return findings


def _scan_file(root: Path, file: Path, policy: dict) -> list[Finding]:
    """Scan one file; a file that is not UTF-8 is a finding, never a crash."""
    relative = file.relative_to(root).as_posix()
    try:
        source = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [Finding(relative, 1, "BOUNDARY_SYNTAX", "undecodable")] if _rules_for(relative, policy) else []
    return scan_source(relative, source, policy)


def new_findings(
    current: list[Finding], base_source: Callable[[str], Optional[str]], policy: dict
) -> list[Finding]:
    """Return the findings that exceed the same file's count at the base."""
    fresh: list[Finding] = []
    for path in sorted({finding.path for finding in current}):
        source = base_source(path)
        base = Counter(f.signature() for f in scan_source(path, source, policy)) if source else Counter()
        for finding in (f for f in current if f.path == path):
            if base[finding.signature()] > 0:
                base[finding.signature()] -= 1
            else:
                fresh.append(finding)
    return fresh


def _git(*args: str) -> subprocess.CompletedProcess:
    """Run git in the repository; a missing git binary blocks the gate."""
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    except OSError as error:
        raise GateBlocked("BOUNDARY_GIT_UNAVAILABLE") from error


def git_source_at(revision: str) -> Callable[[str], Optional[str]]:
    """Return a reader of a file's source at `revision` (None when absent there).

    Raises:
        GateBlocked: git is missing, this is not a repository, or `revision`
            is unknown - the base cannot be read, so nothing can be vouched for.
    """
    if _git("cat-file", "-e", f"{revision}^{{commit}}").returncode != 0:
        raise GateBlocked("BOUNDARY_BASE_UNREADABLE")
    prefix = _git("rev-parse", "--show-prefix").stdout.strip()

    def read(path: str) -> Optional[str]:
        result = _git("show", f"{revision}:{prefix}{path}")
        return result.stdout if result.returncode == 0 else None

    return read


def load_policy(path: Path = POLICY_PATH) -> dict:
    """Read the policy and refuse a base that is not a pinned full commit SHA."""
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise GateBlocked("BOUNDARY_POLICY_UNREADABLE") from error
    if not _SHA.match(str(policy.get("base_commit", ""))):
        raise GateBlocked("BOUNDARY_BASE_MISSING_OR_INVALID")
    return policy


def main(argv: Optional[list[str]] = None) -> int:
    """Run the gate and return its exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="list every finding, debt included")
    args = parser.parse_args(argv)
    try:
        policy = load_policy()
        current = scan_tree(ROOT, policy)
        reported = current if args.full else new_findings(current, git_source_at(policy["base_commit"]), policy)
    except GateBlocked as error:
        print("ENGINE_BOUNDARY_BLOCKED", error.code)
        return 2
    for finding in reported:
        print(finding)
    print("ENGINE_BOUNDARY_FINDINGS" if args.full else "ENGINE_BOUNDARY_NEW_FINDINGS", len(reported))
    return 1 if reported and not args.full else 0


if __name__ == "__main__":
    sys.exit(main())

"""Reject destructive statements in seeders and forward migrations."""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTRUCTIVE_SQL = re.compile(r"\b(?:DELETE\s+FROM|TRUNCATE(?:\s+TABLE)?|DROP\s+(?:TABLE|DATABASE|VIEW))\b", re.I)
DESTRUCTIVE_CALLS = {"drop_table", "drop_all_tables", "truncate"}


def _forward_nodes(path: Path) -> list[ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if path.parent.name == "migrations":
        return [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "up"]
    return [tree]


def check() -> list[str]:
    """Return destructive operations found in seeders or forward migrations."""
    findings = []
    for directory in (ROOT / "database/seeders", ROOT / "database/migrations"):
        for path in directory.glob("*.py"):
            for scope in _forward_nodes(path):
                for node in ast.walk(scope):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) and DESTRUCTIVE_SQL.search(node.value):
                        findings.append(f"{path.relative_to(ROOT)}:{node.lineno}: destructive SQL")
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        if node.func.attr in DESTRUCTIVE_CALLS:
                            findings.append(f"{path.relative_to(ROOT)}:{node.lineno}: {node.func.attr} call")
    return findings


if __name__ == "__main__":
    problems = check()
    for problem in problems:
        print(problem)
    if problems:
        raise SystemExit(1)
    print("Forward migration and seeder safety: clean.")

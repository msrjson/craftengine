#!/usr/bin/env python3
"""Team board gate - keeps `.claude/team/board.md` well formed and append-only.

Every line after the `---` separator must read
`YYYY-MM-DDTHH:MMZ | from: <agent>@<tool> | to: all|<agent>@<tool> | KIND | message`
with a known KIND. With `--staged` it also refuses a commit that edits or
removes a line already in `HEAD`: the board is append-only. With `--hook` it
reads a Claude Code PostToolUse payload from stdin and runs only when the tool
touched the board.

Usage
-----
    python3 .claude/rules/lint_board.py            # the board in the working tree
    python3 .claude/rules/lint_board.py --staged   # plus append-only check (pre-commit)
    python3 .claude/rules/lint_board.py --hook     # Claude Code hook (exit 2 on failure)

Exit codes: 0 clean, 1 violations, 2 violations in hook mode.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ".claude/team/board.md"
SEPARATOR = "---"
KINDS = {"CLAIM", "RELEASE", "BLOCKER", "FINDING", "RED-TEST", "TEST-RUN", "HANDOVER", "DONE", "RULE", "ACK"}
NAME = r"(?:owner|[a-z0-9-]+@[a-z0-9-]+)"
LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z \| from: " + NAME
    + r" \| to: (?:all|" + NAME + r") \| ([A-Z-]+) \| \S.*$"
)
CATALOG = {
    "LINE": "{path}:{line}: {rule} {message}",
    "SUMMARY": "Team board: {count} violation(s). See handoff.md",
    "CLEAN": "Team board: clean.",
    "MISSING": "board file is missing",
    "NO_SEPARATOR": "no '---' line separates the header from the notices",
    "FORMAT": "line does not match 'UTC | from: agent@tool | to: all|agent@tool | KIND | message'",
    "KIND": "unknown kind",
    "REWRITTEN": "a committed line was edited, reordered or removed; the board is append-only",
}


def notices(text: str) -> list[tuple[int, str]] | None:
    """Return (line number, text) of every notice, or None without a separator."""
    lines = text.splitlines()
    if SEPARATOR not in lines:
        return None
    start = lines.index(SEPARATOR) + 1
    return [(number, line) for number, line in enumerate(lines[start:], start + 1) if line.strip()]


def check_text(text: str) -> list[tuple[str, int, str]]:
    """Return (rule, line, message) for every malformed notice."""
    found = notices(text)
    if found is None:
        return [("BOARD-SEP", 1, CATALOG["NO_SEPARATOR"])]
    problems = []
    for number, line in found:
        match = LINE.match(line)
        if match is None:
            problems.append(("BOARD-FORMAT", number, CATALOG["FORMAT"]))
        elif match.group(1) not in KINDS:
            problems.append(("BOARD-KIND", number, CATALOG["KIND"]))
    return problems


def check_append_only(committed: str, staged: str) -> list[tuple[str, int, str]]:
    """The staged board must start with every committed line, in order."""
    old, new = committed.splitlines(), staged.splitlines()
    if new[: len(old)] == old:
        return []
    first = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
    return [("BOARD-APPEND", first + 1, CATALOG["REWRITTEN"])]


def _git_show(spec: str) -> str | None:
    result = subprocess.run(["git", "show", spec], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else None


def check(staged: bool) -> list[tuple[str, int, str]]:
    path = ROOT / BOARD
    if not path.is_file():
        return [("BOARD-MISSING", 1, CATALOG["MISSING"])]
    problems = check_text(path.read_text(encoding="utf-8"))
    if staged:
        committed, index = _git_show(f"HEAD:{BOARD}"), _git_show(f":{BOARD}")
        if committed is not None and index is not None:
            problems += check_append_only(committed, index)
    return problems


def _hook_is_relevant() -> bool:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return True
    tool_input = payload.get("tool_input") or {}
    target = " ".join(str(tool_input.get(key, "")) for key in ("file_path", "command"))
    return "board.md" in target


def main(argv: list[str]) -> int:
    """Run the gate and print violations; return the process exit code."""
    hook = "--hook" in argv
    if hook and not _hook_is_relevant():
        return 0
    found = check("--staged" in argv)
    if not found:
        print(CATALOG["CLEAN"])
        return 0
    stream = sys.stderr if hook else sys.stdout
    for rule, line, message in found:
        print(CATALOG["LINE"].format(path=BOARD, line=line, rule=rule, message=message), file=stream)
    print(CATALOG["SUMMARY"].format(count=len(found)), file=stream)
    return 2 if hook else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

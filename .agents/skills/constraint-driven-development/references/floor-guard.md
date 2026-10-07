# Floor guard: reference implementation

Every numbered dimension in `CONSTRAINTS.md` maps to a de facto tool (Step 4 of the
skill). The **floor** does not: it is a diff-scoped check for the five moves in
Step 6, and without a shipped reference every agent invents its own, so two runs
(or two projects) produce two different guards. That is exactly the
non-determinism the skill exists to remove.

This is the reference. Adapt the patterns to your project; keep the contract
identical.

## Contract

- **Input:** the diff between the merge base and the working tree (added *and*
  removed lines, plus untracked files). A guard that reads only `git diff` misses
  new files and staged-but-uncommitted work.
- **Detects the five Step 6 moves:** a weakened threshold in `CONSTRAINTS.md` or a
  gate configuration, a test made easier (a skip marker, a deleted test file, an
  assertion removed from a test that stayed), a silenced checker (a new suppression
  comment), unfinished work (a stub or a swallowed exception), a new Exceptions row.
- **Also enforces the Craft floor extras:** no destructive database command
  (`migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe`, `db:drop`) added
  to code, scripts or CI, and no bare or broad `except`.
- **Exit codes:** `0` clean, `1` at least one floor violation (block the change),
  `2` the guard could not run (no merge base, not a git repository). Never let a `2`
  read as a `0`.
- **Reports the rule and the location, never a matched secret value.** Redaction is
  not optional (Step 4); lines are truncated and never echo whole payloads.
- **Tightening is silent, loosening is loud:** only moves that lower the bar surface.

## Reference (Python 3.14, standard library only)

Save it outside the production tree, for example as `tools/floor_guard.py` in the
repository tooling, and run it from the repository root. It follows the same
governance as application code: typed signatures, Google docstrings, short
functions, no broad `except`.

```python
"""Diff-scoped enforcement of the CONSTRAINTS.md floor.

Usage:
    python tools/floor_guard.py [--base <ref>]   (default base: origin/main)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

EXIT_CLEAN = 0
EXIT_VIOLATION = 1
EXIT_CANNOT_RUN = 2

# 1. Silenced checker. Extend for your tooling.
SUPPRESSIONS = re.compile(
    r"#\s*noqa|#\s*type:\s*ignore|pragma:\s*no\s*(cover|mutate)|#\s*nosec"
    r"|nosemgrep|gitleaks:allow|lint-language:\s*ignore|ruff:\s*noqa"
)
# 4. Unfinished work, plus the broad-except floor rule.
STUBS = re.compile(r"raise\s+NotImplementedError|\bTODO\b|^\s*except\s*:|except\s+(Base)?Exception\s*:")
SWALLOW = re.compile(r"^\s*except\b.*:\s*(pass|\.\.\.)\s*$")
# 2. A test made easier.
SKIPS = re.compile(r"@pytest\.mark\.(skip|skipif|xfail)|pytest\.skip\(|@unittest\.skip")
# Craft floor extra: destructive database commands.
DESTRUCTIVE = re.compile(r"\b(migrate:(fresh|reset|refresh)|db:(wipe|drop))\b")
ASSERTION = re.compile(r"^\s*(assert\b|self\.assert\w*\(|pytest\.raises\()")
EXCEPTION_ROW = re.compile(r"^\|\s*[WE]\d+\s*\|")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
THRESHOLD_FILES = ("CONSTRAINTS.md", "language-standard.toml", "pyproject.toml")


@dataclass(frozen=True)
class DiffLine:
    """One added or removed line of the diff."""

    path: str
    text: str


@dataclass(frozen=True)
class Finding:
    """A floor violation located in the diff."""

    rule: str
    path: str
    text: str


class GuardCannotRunError(RuntimeError):
    """Raised when the diff cannot be computed."""


def run_git(args: list[str], *, allow_diff_exit: bool = False) -> str:
    """Run a git command and return its standard output.

    Args:
        args: Arguments passed to git.
        allow_diff_exit: Accept exit code 1, which `git diff --no-index` uses for "differs".

    Returns:
        The command output.

    Raises:
        GuardCannotRunError: If git is missing or the command fails.
    """
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise GuardCannotRunError("git executable not found") from error
    accepted = {0, 1} if allow_diff_exit else {0}
    if result.returncode not in accepted:
        raise GuardCannotRunError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def collect_diff(base: str) -> str:
    """Return the unified diff against the merge base, including untracked files.

    Args:
        base: The reference to compare against.

    Returns:
        The combined diff text.
    """
    merge_base = run_git(["merge-base", base, "HEAD"]).strip()
    tracked = run_git(["diff", "--unified=0", merge_base, "--"])
    untracked = run_git(["ls-files", "--others", "--exclude-standard"]).splitlines()
    new_files = [
        run_git(["diff", "--no-index", "--unified=0", "/dev/null", path], allow_diff_exit=True)
        for path in untracked
    ]
    return "\n".join([tracked, *new_files])


def split_diff(diff: str) -> tuple[list[DiffLine], list[DiffLine]]:
    """Split a unified diff into added and removed lines.

    Args:
        diff: Unified diff text.

    Returns:
        A pair of (added, removed) lines.
    """
    added: list[DiffLine] = []
    removed: list[DiffLine] = []
    path = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(DiffLine(path, line[1:]))
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(DiffLine(path, line[1:]))
    return added, removed


def is_test_file(path: str) -> bool:
    """Return whether a path is a pytest module.

    Args:
        path: Repository-relative path.

    Returns:
        True for `test_*.py` and `*_test.py` files.
    """
    name = path.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def check_added(line: DiffLine) -> list[str]:
    """Return the floor rules broken by one added line.

    Args:
        line: The added line.

    Returns:
        Rule identifiers, possibly empty.
    """
    checks = {
        "silenced-checker": SUPPRESSIONS,
        "unfinished-work": STUBS,
        "swallowed-exception": SWALLOW,
        "test-made-easier": SKIPS,
        "destructive-database-command": DESTRUCTIVE,
    }
    rules = [rule for rule, pattern in checks.items() if pattern.search(line.text)]
    if line.path.endswith("CONSTRAINTS.md") and EXCEPTION_ROW.search(line.text):
        rules.append("new-exception")
    return rules


def threshold_lowered(old: str, new: str) -> bool:
    """Return whether any number in a matching line went down.

    Args:
        old: The removed version of the line.
        new: The added version of the line.

    Returns:
        True when a positionally matching number is smaller in the new line.
    """
    old_numbers = [float(value) for value in NUMBER.findall(old)]
    new_numbers = [float(value) for value in NUMBER.findall(new)]
    return any(after < before for before, after in zip(old_numbers, new_numbers))


def line_key(text: str) -> str:
    """Return the label part of a table row or `key = value` line.

    Args:
        text: The line text.

    Returns:
        The text before the first separator, stripped.
    """
    return re.split(r"[|:=]", text.strip("| "), maxsplit=1)[0].strip()


def find_lowered_thresholds(added: list[DiffLine], removed: list[DiffLine]) -> list[Finding]:
    """Find threshold lines whose numbers decreased in constraint or gate files.

    Args:
        added: Added lines of the diff.
        removed: Removed lines of the diff.

    Returns:
        One finding per weakened threshold.
    """
    watched = [line for line in added if line.path.endswith(THRESHOLD_FILES)]
    findings: list[Finding] = []
    for old in (line for line in removed if line.path.endswith(THRESHOLD_FILES)):
        match = next((new for new in watched if new.path == old.path and line_key(new.text) == line_key(old.text)), None)
        if match and threshold_lowered(old.text, match.text):
            findings.append(Finding("threshold-lowered", old.path, f"{old.text} -> {match.text}"))
    return findings


def collect_findings(added: list[DiffLine], removed: list[DiffLine]) -> list[Finding]:
    """Apply every floor rule to the diff.

    Args:
        added: Added lines of the diff.
        removed: Removed lines of the diff.

    Returns:
        Every floor violation found.
    """
    findings = [Finding(rule, line.path, line.text) for line in added for rule in check_added(line)]
    findings += [
        Finding("assertion-removed", line.path, line.text)
        for line in removed
        if is_test_file(line.path) and ASSERTION.search(line.text)
    ]
    return findings + find_lowered_thresholds(added, removed)


def report(findings: list[Finding]) -> int:
    """Print the findings and return the process exit code.

    Args:
        findings: The floor violations.

    Returns:
        `EXIT_CLEAN` or `EXIT_VIOLATION`.
    """
    if not findings:
        print("floor-guard: clean")
        return EXIT_CLEAN
    print(f"floor-guard: {len(findings)} floor violation(s):", file=sys.stderr)
    for finding in findings:
        print(f"  [{finding.rule}] {finding.path}: {finding.text.strip()[:120]}", file=sys.stderr)
    print("Each is a move that lowers the bar. Fix the code, or route it through a tracked exception.", file=sys.stderr)
    return EXIT_VIOLATION


def main() -> int:
    """Run the floor guard against the merge base.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(description="Diff-scoped CONSTRAINTS.md floor guard.")
    parser.add_argument("--base", default="origin/main")
    base = parser.parse_args().base
    try:
        diff = collect_diff(base)
    except GuardCannotRunError as error:
        print(f"floor-guard: cannot run against {base}: {error}", file=sys.stderr)
        return EXIT_CANNOT_RUN
    return report(collect_findings(*split_diff(diff)))


if __name__ == "__main__":
    sys.exit(main())
```

The guard's own source contains every pattern it hunts for, so exclude its own
path (see `.constraintsignore` below) or it will flag itself the first time it is
committed.

## Adapting it

- **Patterns are the only project-specific part.** Add your tooling's suppression
  and stub forms to the regular expressions (for example a vendored JavaScript
  linter's disable comment in `public/` assets); the diff plumbing, the
  `CONSTRAINTS.md` checks and the exit codes stay as they are.
- **Watch the files that hold your thresholds.** `THRESHOLD_FILES` covers
  `CONSTRAINTS.md`, the language gate configuration and `pyproject.toml`
  (`[tool.ruff]`, coverage settings). Add the structure gate configuration and any
  import-linter contract file your project uses.
- **A `.constraintsignore`** (one glob per line) exempts a path the guard would
  otherwise flag; check each line's path against it with `fnmatch` before flagging,
  so a genuine exception is a tracked file rather than a loosened rule.
- **Wire it into the fast tier.** Add it as a local hook in
  `.pre-commit-config.yaml` and as a CI step; exit `2` must fail the job, never pass it.
- **This is a starting point, not a finished tool.** It is deliberately
  regex-shallow: it catches the cheap-road-to-green moves agents actually make, not
  a determined human hiding a change. That is the right trade for a check that runs
  on every diff. Once you outgrow it, move to a real runner (Escalation Path level 3).

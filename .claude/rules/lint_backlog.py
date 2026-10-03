#!/usr/bin/env python3
"""Backlog queue gate - enforces `.claude/rules/BACKLOG_QUEUE_STANDARD.md`.

Validates every file under `backlog/`: directory, file name, front matter,
UTC timestamps, append-only History, claim and closing invariants. With
`--staged` it also reads the Git index to refuse deleted tasks, renamed tasks
and rewritten History lines. With `--hook` it reads a Claude Code PostToolUse
payload from stdin and runs only when the tool touched `backlog/`.

Usage
-----
    python3 .claude/rules/lint_backlog.py            # whole queue
    python3 .claude/rules/lint_backlog.py --staged   # plus Git index checks (pre-commit)
    python3 .claude/rules/lint_backlog.py --hook     # Claude Code hook (exit 2 on failure)

Exit codes: 0 clean, 1 violations, 2 violations in hook mode.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "backlog"
TASK_DIRS = ("bugfix", "pending", "processing", "done", "failed")
ALL_DIRS = TASK_DIRS + ("resolutions",)
ROOT_FILES = {"README.md", "TEMPLATE.md"}
KEEP = ".gitkeep"

TASK_NAME = re.compile(r"^p([1-3])-(\d{8}-\d{6})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HISTORY_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) \S")
REQUIRED = ("id", "title", "type", "priority", "autonomous", "blocked_by",
            "max_attempts", "attempts", "created_at", "updated_at", "source", "touches")
TYPES = {"bugfix", "feature", "chore", "decision"}
BLOCKERS = {"none", "owner-decision", "owner-action"}
OUTCOMES = {"resolved", "obsolete"}

Violation = tuple[str, str, str]  # (rule, path, message)

#: Engineer-facing gate messages: one catalog, code -> template with named
#: placeholders, the same pattern as `engine/support/diagnostics.py`.
CATALOG = {
    "QUEUE_MISSING": "the queue directory is missing",
    "DIR_UNKNOWN": "unknown directory; allowed: {allowed}",
    "DIR_ROOT_FILE": "task files live in a state directory, not the queue root",
    "DIR_NESTED": "nested directories are not allowed",
    "FIELD_MISSING": "missing front matter field `{field}`",
    "FIELD_MUST_EQUAL": "`{field}` must be {expected}",
    "FIELD_ONE_OF": "`{field}` must be one of {allowed}",
    "FIELD_BOOLEAN": "`autonomous` must be true or false",
    "FIELD_INTEGERS": "`attempts`/`max_attempts` must be integers",
    "FIELD_EMPTY": "`title` and `source` must not be empty",
    "BLOCKED_AUTONOMOUS": "a blocked task cannot be autonomous",
    "HISTORY_MISSING": "`## History` is missing or empty",
    "HISTORY_MALFORMED": "malformed History line: {line}",
    "HISTORY_ORDER": "History lines are not in chronological order",
    "TIME_FORMAT": "`created_at`/`updated_at` must be ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)",
    "TIME_UPDATED": "`updated_at` must equal the last History line ({stamp})",
    "TIME_BEFORE_CREATED": "History starts before `created_at`",
    "ATTEMPTS_EXCEEDED": "attempts ({attempts}) exceed max_attempts ({limit})",
    "CLAIM_INCOMPLETE": "a task in processing/ needs `claimed_by` and attempts >= 1",
    "CLAIM_NOT_ALLOWED": "only autonomous, unblocked tasks may be claimed",
    "RESOLUTION_MISSING": "missing resolutions/{stem}.resolution.md",
    "FAILURE_LOG_MISSING": "missing failed/{stem}.log.md",
    "NAME_TASK": "name must be p<1-3>-<YYYYMMDD-HHMMSS>-<kebab-slug>.md",
    "NAME_RESOLUTION": "name must be <task-file-name>.resolution.md",
    "FRONT_MATTER_MISSING": "front matter block (---) is missing",
    "RESOLUTION_ORPHAN": "no matching task done/{task}.md",
    "RESOLUTION_TIME": "`started_at`/`finished_at` must be ISO 8601 UTC",
    "VERIFICATION_MISSING": "missing `## Verification` section",
    "FAILURE_LOG_ORPHAN": "failure log without its task in failed/",
    "DUPLICATE_ID": "task id {task_id} also in {other}",
    "TASK_DELETED": "tasks are never deleted; move them to done/ or failed/",
    "TASK_RENAMED": "a task is never renamed (was {old})",
    "HISTORY_REWRITTEN": "committed History lines were changed or removed; only append",
    "SUMMARY": "Backlog queue: {count} violation(s). See .claude/rules/BACKLOG_QUEUE_STANDARD.md",
    "LINE": "{path}: {rule} {message}",
}


def _v(rule: str, path: str, message_code: str, **params: object) -> tuple[str, str, str]:
    """Build one violation from the catalog."""
    return (rule, path, CATALOG[message_code].format(**params))



def _rel(path: Path) -> str:
    """Return `path` relative to the workspace root for messages."""
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def parse_front_matter(text: str) -> dict[str, str] | None:
    """Parse the simple `key: value` front matter the queue uses.

    Args:
        text: Full file content.

    Returns:
        The fields as strings (list fields joined by newlines), or None when the
        file does not start with a `---` block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in [l.strip() for l in lines[1:]]:
        return None
    end = 1 + [l.strip() for l in lines[1:]].index("---")
    fields: dict[str, str] = {}
    key = ""
    for line in lines[1:end]:
        if line.startswith("  - ") and key:
            fields[key] = (fields[key] + "\n" + line[4:].strip()).strip()
        elif ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip().strip('"')
    return fields


def history_lines(text: str) -> list[str] | None:
    """Return the bullet lines of `## History`, or None when the section is missing."""
    marker = "\n## History\n"
    if marker not in text:
        return None
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    return [line.rstrip() for line in section.splitlines() if line.startswith("- ")]


def _to_iso(stamp: str) -> str:
    """Convert a `YYYYMMDD-HHMMSS` id to ISO 8601 UTC."""
    moment = datetime.strptime(stamp, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def check_layout() -> list[Violation]:
    """BQ-DIR: only the six queue directories and the two root documents."""
    found: list[Violation] = []
    if not QUEUE.is_dir():
        return [_v("BQ-DIR", "backlog", "QUEUE_MISSING")]
    for entry in QUEUE.iterdir():
        if entry.is_dir() and entry.name not in ALL_DIRS:
            found.append(_v("BQ-DIR", _rel(entry), "DIR_UNKNOWN", allowed=", ".join(ALL_DIRS)))
        if entry.is_file() and entry.name not in ROOT_FILES:
            found.append(_v("BQ-DIR", _rel(entry), "DIR_ROOT_FILE"))
    for name in ALL_DIRS:
        for entry in (QUEUE / name).glob("*") if (QUEUE / name).is_dir() else []:
            if entry.is_dir():
                found.append(_v("BQ-DIR", _rel(entry), "DIR_NESTED"))
    return found


def _check_meta(path: Path, meta: dict[str, str], match: re.Match[str]) -> list[Violation]:
    """BQ-META and BQ-AUTO: fields present, well-formed and consistent with the name."""
    rel = _rel(path)
    found = [_v("BQ-META", rel, "FIELD_MISSING", field=key) for key in REQUIRED if key not in meta]
    if found:
        return found
    priority, stamp = match.group(1), match.group(2)
    checks = [
        (meta["id"] == stamp, ("FIELD_MUST_EQUAL", {"field": "id", "expected": stamp})),
        (meta["priority"] == priority, ("FIELD_MUST_EQUAL", {"field": "priority", "expected": priority})),
        (meta["type"] in TYPES, ("FIELD_ONE_OF", {"field": "type", "allowed": sorted(TYPES)})),
        (meta["blocked_by"] in BLOCKERS, ("FIELD_ONE_OF", {"field": "blocked_by", "allowed": sorted(BLOCKERS)})),
        (meta["autonomous"] in {"true", "false"}, ("FIELD_BOOLEAN", {})),
        (meta["attempts"].isdigit() and meta["max_attempts"].isdigit(), ("FIELD_INTEGERS", {})),
        (meta["created_at"] == _to_iso(stamp), ("FIELD_MUST_EQUAL", {"field": "created_at", "expected": _to_iso(stamp)})),
        (bool(meta["title"]) and bool(meta["source"]), ("FIELD_EMPTY", {})),
    ]
    found = [_v("BQ-META", rel, code, **params) for ok, (code, params) in checks if not ok]
    if meta["blocked_by"] != "none" and meta["autonomous"] == "true":
        found.append(_v("BQ-AUTO", rel, "BLOCKED_AUTONOMOUS"))
    return found


def _check_history(path: Path, meta: dict[str, str], lines: list[str] | None) -> list[Violation]:
    """BQ-HIST and BQ-TIME: History present, well-formed, ordered, matching `updated_at`."""
    rel = _rel(path)
    if not lines:
        return [_v("BQ-HIST", rel, "HISTORY_MISSING")]
    stamps: list[str] = []
    for line in lines:
        parsed = HISTORY_LINE.match(line)
        if not parsed:
            return [_v("BQ-HIST", rel, "HISTORY_MALFORMED", line=repr(line))]
        stamps.append(parsed.group(1))
    found: list[Violation] = []
    if stamps != sorted(stamps):
        found.append(_v("BQ-TIME", rel, "HISTORY_ORDER"))
    updated = meta.get("updated_at", "")
    if not ISO.match(updated) or not ISO.match(meta.get("created_at", "")):
        found.append(_v("BQ-TIME", rel, "TIME_FORMAT"))
    elif updated != stamps[-1]:
        found.append(_v("BQ-TIME", rel, "TIME_UPDATED", stamp=stamps[-1]))
    if stamps[0] < meta.get("created_at", ""):
        found.append(_v("BQ-TIME", rel, "TIME_BEFORE_CREATED"))
    return found


def _check_state(path: Path, meta: dict[str, str]) -> list[Violation]:
    """BQ-CLAIM and BQ-CLOSE: invariants that depend on the task's directory."""
    rel, state, stem = _rel(path), path.parent.name, path.name[:-3]
    found: list[Violation] = []
    attempts, limit = int(meta.get("attempts", "0") or 0), int(meta.get("max_attempts", "0") or 0)
    if attempts > limit:
        found.append(_v("BQ-CLAIM", rel, "ATTEMPTS_EXCEEDED", attempts=attempts, limit=limit))
    if state == "processing" and (not meta.get("claimed_by") or attempts < 1):
        found.append(_v("BQ-CLAIM", rel, "CLAIM_INCOMPLETE"))
    if state == "processing" and (meta.get("autonomous") != "true" or meta.get("blocked_by") != "none"):
        found.append(_v("BQ-CLAIM", rel, "CLAIM_NOT_ALLOWED"))
    if state == "done" and not (QUEUE / "resolutions" / f"{stem}.resolution.md").is_file():
        found.append(_v("BQ-CLOSE", rel, "RESOLUTION_MISSING", stem=stem))
    if state == "failed" and not (QUEUE / "failed" / f"{stem}.log.md").is_file():
        found.append(_v("BQ-CLOSE", rel, "FAILURE_LOG_MISSING", stem=stem))
    return found


def check_task(path: Path) -> list[Violation]:
    """Validate one task file in a state directory."""
    match = TASK_NAME.match(path.name)
    if not match:
        return [_v("BQ-NAME", _rel(path), "NAME_TASK")]
    text = path.read_text(encoding="utf-8")
    meta = parse_front_matter(text)
    if meta is None:
        return [_v("BQ-META", _rel(path), "FRONT_MATTER_MISSING")]
    found = _check_meta(path, meta, match)
    found += _check_history(path, meta, history_lines(text))
    return found + _check_state(path, meta)


def check_resolution(path: Path) -> list[Violation]:
    """BQ-CLOSE: a resolution report belongs to a task in done/ and carries evidence."""
    rel, task = _rel(path), path.name.removesuffix(".resolution.md")
    if not path.name.endswith(".resolution.md") or not TASK_NAME.match(f"{task}.md"):
        return [_v("BQ-NAME", rel, "NAME_RESOLUTION")]
    found: list[Violation] = []
    if not (QUEUE / "done" / f"{task}.md").is_file():
        found.append(_v("BQ-CLOSE", rel, "RESOLUTION_ORPHAN", task=task))
    text = path.read_text(encoding="utf-8")
    meta = parse_front_matter(text) or {}
    for key in ("task", "outcome", "agent", "started_at", "finished_at"):
        if not meta.get(key):
            found.append(_v("BQ-META", rel, "FIELD_MISSING", field=key))
    if meta.get("task") and meta["task"] != task:
        found.append(_v("BQ-META", rel, "FIELD_MUST_EQUAL", field="task", expected=task))
    if meta.get("outcome") and meta["outcome"] not in OUTCOMES:
        found.append(_v("BQ-META", rel, "FIELD_ONE_OF", field="outcome", allowed=sorted(OUTCOMES)))
    if any(meta.get(k) and not ISO.match(meta[k]) for k in ("started_at", "finished_at")):
        found.append(_v("BQ-TIME", rel, "RESOLUTION_TIME"))
    if "\n## Verification\n" not in text:
        found.append(_v("BQ-CLOSE", rel, "VERIFICATION_MISSING"))
    return found


def check_queue() -> list[Violation]:
    """Run every file-level check over the queue."""
    found = check_layout()
    seen: dict[str, str] = {}
    for state in TASK_DIRS:
        for path in sorted((QUEUE / state).glob("*")) if (QUEUE / state).is_dir() else []:
            if path.name == KEEP or path.is_dir():
                continue
            if state == "failed" and path.name.endswith(".log.md"):
                if not (QUEUE / "failed" / path.name.replace(".log.md", ".md")).is_file():
                    found.append(_v("BQ-CLOSE", _rel(path), "FAILURE_LOG_ORPHAN"))
                continue
            found += check_task(path)
            match = TASK_NAME.match(path.name)
            if match and match.group(2) in seen:
                found.append(_v("BQ-DUP", _rel(path), "DUPLICATE_ID", task_id=match.group(2), other=seen[match.group(2)]))
            elif match:
                seen[match.group(2)] = _rel(path)
    resolutions = QUEUE / "resolutions"
    for path in sorted(resolutions.glob("*")) if resolutions.is_dir() else []:
        if path.name != KEEP:
            found += check_resolution(path)
    return found


def _git(*args: str) -> str:
    """Run a git command in the workspace and return stdout ('' on failure)."""
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else ""


def check_staged() -> list[Violation]:
    """BQ-DEL, BQ-NAME and BQ-HIST against the Git index."""
    found: list[Violation] = []
    for row in _git("diff", "--cached", "--name-status", "-M", "--", "backlog/").splitlines():
        parts = row.split("\t")
        status, old, new = parts[0], parts[1], parts[-1]
        if not TASK_NAME.match(Path(old).name) or Path(old).parent.name not in TASK_DIRS:
            continue
        if status == "D":
            found.append(_v("BQ-DEL", old, "TASK_DELETED"))
            continue
        if status.startswith("R") and Path(old).name != Path(new).name:
            found.append(_v("BQ-NAME", new, "TASK_RENAMED", old=Path(old).name))
        before = history_lines(_git("show", f"HEAD:{old}")) or []
        after = history_lines(_git("show", f":{new}")) or []
        if after[: len(before)] != before:
            found.append(_v("BQ-HIST", new, "HISTORY_REWRITTEN"))
    return found


def _hook_is_relevant() -> bool:
    """Read a Claude Code hook payload and say whether it touched the queue."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return True
    tool_input = payload.get("tool_input") or {}
    target = " ".join(str(tool_input.get(k, "")) for k in ("file_path", "command", "notebook_path"))
    return re.search(r"\bbacklog\b(?!\.md)", target) is not None


def main(argv: list[str]) -> int:
    """Run the gate and print violations; return the process exit code."""
    hook = "--hook" in argv
    if hook and not _hook_is_relevant():
        return 0
    found = check_queue() + (check_staged() if "--staged" in argv else [])
    if not found:
        print("Backlog queue: clean.")
        return 0
    stream = sys.stderr if hook else sys.stdout
    for rule, path, message in found:
        print(CATALOG["LINE"].format(path=path, rule=rule, message=message), file=stream)
    print(CATALOG["SUMMARY"].format(count=len(found)), file=stream)
    return 2 if hook else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

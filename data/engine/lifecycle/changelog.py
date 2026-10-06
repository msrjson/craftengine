"""Upgrade notes: the changelog sections a move crosses, and what in them needs care.

The changelog follows Keep a Changelog with `## [X.Y.Z] rNNNNN - date`
headings (NR-04). An upgrade shows every section after the current version up
to the target, and calls out the categories that can break a project.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from engine.lifecycle.release import Release, Version

#: A release heading; `[Unreleased]` does not match and is never shown.
SECTION_HEADING = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\]")

#: Categories whose entries a project must read before it moves.
ATTENTION_CATEGORIES = frozenset({"Removed", "Deprecated", "Security", "Changed"})


@dataclass
class Section:
    """One release's changelog section.

    Args:
        version: The release version.
        heading: The heading line as written.
        attention: First lines of entries under an attention category,
            prefixed with the category.
    """

    version: Version
    heading: str
    attention: list[str] = field(default_factory=list)


def _split_sections(text: str) -> list[tuple[Version, list[str]]]:
    """Return each release section as its version and lines, in file order."""
    sections: list[tuple[Version, list[str]]] = []
    for line in text.splitlines():
        match = SECTION_HEADING.match(line)
        if match:
            sections.append((tuple(int(group) for group in match.groups()), [line]))  # type: ignore[arg-type]
        elif sections:
            sections[-1][1].append(line)
    return sections


def _attention_entries(lines: list[str]) -> list[str]:
    """Return the first line of every entry under an attention category."""
    entries: list[str] = []
    category = ""
    for line in lines:
        if line.startswith("### "):
            category = line[4:].strip()
        elif line.startswith("- ") and category in ATTENTION_CATEGORIES:
            entries.append(f"{category}: {line[2:].strip()}")
    return entries


def sections_between(text: str, after: Version, upto: Version) -> list[Section]:
    """Return the sections of releases newer than `after` and not newer than `upto`.

    Args:
        text: The target release's `CHANGELOG.md`.
        after: The version the project runs.
        upto: The version it moves to.

    Returns:
        The crossed sections, newest first, as the changelog orders them.
    """
    return [
        Section(version, lines[0], _attention_entries(lines[1:]))
        for version, lines in _split_sections(text)
        if after < version <= upto
    ]


def crossed_sections(tree: Path, current: Release, target: Release) -> list[Section]:
    """Return the changelog sections a move crosses; none when the release has no changelog."""
    changelog = tree / "CHANGELOG.md"
    if not changelog.is_file():
        return []
    return sections_between(changelog.read_text(encoding="utf-8"), current.version, target.version)


__all__ = ["ATTENTION_CATEGORIES", "Section", "crossed_sections", "sections_between"]

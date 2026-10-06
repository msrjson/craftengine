"""Release identity: the `vMAJOR.MINOR.PATCH-rNNNNN` tag and how releases compare.

The tag format is the one NR-01 fixes for every cut release. Releases order by
semantic version first and by the monotonic counter second, so a hotfix release
cut later on an older line still sorts by the version it carries.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from engine.lifecycle.errors import EngineLifecycleError

#: A release tag as NR-01 defines it.
RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-r(\d{5})$")

#: A bare semantic version, as typed after `upgrade --to`.
VERSION_TEXT = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

Version = tuple[int, int, int]


@dataclass(frozen=True, order=True)
class Release:
    """One published engine release.

    Args:
        version: `(major, minor, patch)`.
        counter: The monotonic release counter (`r00024` is 24).
        ref: The tag that names the release in the canonical repository.
    """

    version: Version
    counter: int
    ref: str = field(compare=False)

    @property
    def version_text(self) -> str:
        """Return the version as `MAJOR.MINOR.PATCH`."""
        return ".".join(str(part) for part in self.version)

    @property
    def release_text(self) -> str:
        """Return the counter as `rNNNNN`."""
        return f"r{self.counter:05d}"


def parse_ref(ref: str) -> Release | None:
    """Return the release a tag names, or None when it is not a release tag.

    Args:
        ref: A tag such as `v4.4.2-r00024`.

    Returns:
        The parsed release, or None.
    """
    match = RELEASE_TAG.match(ref.strip())
    if match is None:
        return None
    major, minor, patch, counter = (int(group) for group in match.groups())
    return Release((major, minor, patch), counter, ref.strip())


def require_ref(ref: str) -> Release:
    """Return the release a tag names.

    Args:
        ref: A tag such as `v4.4.2-r00024`.

    Returns:
        The parsed release.

    Raises:
        EngineLifecycleError: `ENGINE_REF_INVALID` when the tag is not a release tag.
    """
    release = parse_ref(ref)
    if release is None:
        raise EngineLifecycleError("ENGINE_REF_INVALID", ref)
    return release


def parse_version(text: str) -> Version:
    """Return the `(major, minor, patch)` a version string names.

    Args:
        text: `4.5.0` or `v4.5.0`.

    Returns:
        The version tuple.

    Raises:
        EngineLifecycleError: `ENGINE_VERSION_INVALID` for anything else.
    """
    match = VERSION_TEXT.match(text.strip())
    if match is None:
        raise EngineLifecycleError("ENGINE_VERSION_INVALID", text)
    major, minor, patch = (int(group) for group in match.groups())
    return (major, minor, patch)


def releases_from_tags(names: Iterable[str]) -> list[Release]:
    """Return the release tags among `names`, oldest first; other tags are ignored.

    Args:
        names: Tag names as the repository lists them.

    Returns:
        The parsed releases, sorted.
    """
    return sorted(release for release in map(parse_ref, names) if release is not None)


def newest_patch(current: Release, candidates: Iterable[Release]) -> Release | None:
    """Return the newest release on the same `major.minor` line that is newer than `current`.

    Args:
        current: The release the project runs.
        candidates: Every published release.

    Returns:
        The update target, or None when `current` is the newest of its line.
    """
    line = [
        release for release in candidates if release.version[:2] == current.version[:2] and release > current
    ]
    return max(line, default=None)


def newest(candidates: Iterable[Release]) -> Release | None:
    """Return the newest release overall, or None when there is none."""
    return max(candidates, default=None)


def find_version(candidates: Iterable[Release], version: Version) -> Release:
    """Return the release that carries `version` (the latest cut, if several do).

    Args:
        candidates: Every published release.
        version: The version asked for.

    Returns:
        The matching release.

    Raises:
        EngineLifecycleError: `ENGINE_RELEASE_NOT_FOUND` when no release carries it.
    """
    matches = [release for release in candidates if release.version == version]
    if not matches:
        raise EngineLifecycleError("ENGINE_RELEASE_NOT_FOUND", ".".join(map(str, version)))
    return max(matches)


__all__ = [
    "Release",
    "Version",
    "find_version",
    "newest",
    "newest_patch",
    "parse_ref",
    "parse_version",
    "releases_from_tags",
    "require_ref",
]

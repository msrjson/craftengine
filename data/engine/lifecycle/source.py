"""Fetching releases from the canonical source: the tag list and tag archives.

Only the standard library is used - the application container has no git, and
the engine does not depend on one. Only `https` and `file` URLs are accepted:
`https` for the canonical repository, `file` for an air-gapped mirror. An
archive is extracted with the safe tarfile extraction filter, so a member cannot escape the
destination through an absolute path, `..` or a link.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import tarfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import Source
from engine.lifecycle.release import Release, releases_from_tags

#: URL schemes a release may come from.
ALLOWED_SCHEMES = frozenset({"https", "file"})

#: Seconds before a network read gives up.
TIMEOUT_SECONDS = 60

#: Release content the lifecycle needs, relative to the source subdirectory.
WANTED_ROOTS = ("engine", "CHANGELOG.md")


def read_url(url: str) -> bytes:
    """Return the body at `url`.

    Args:
        url: An `https://` or `file://` URL.

    Returns:
        The raw bytes.

    Raises:
        EngineLifecycleError: `ENGINE_SOURCE_SCHEME_REFUSED` for another scheme,
            `ENGINE_SOURCE_UNREACHABLE` when the read fails.
    """
    if urlparse(url).scheme not in ALLOWED_SCHEMES:
        raise EngineLifecycleError("ENGINE_SOURCE_SCHEME_REFUSED", url)
    request = urllib.request.Request(url, headers={"User-Agent": "craft-engine-lifecycle"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except (urllib.error.URLError, OSError) as failure:
        raise EngineLifecycleError("ENGINE_SOURCE_UNREACHABLE", f"{url}: {failure}") from None


def list_releases(source: Source) -> list[Release]:
    """Return every release the source publishes, oldest first.

    Args:
        source: Where releases come from.

    Returns:
        The releases; tags that are not release tags are ignored.

    Raises:
        EngineLifecycleError: `ENGINE_SOURCE_INVALID` when the listing is not a
            JSON list of `{"name": ...}` objects.
    """
    try:
        names = [entry["name"] for entry in json.loads(read_url(source.tags_url))]
    except (ValueError, TypeError, KeyError) as malformed:
        raise EngineLifecycleError("ENGINE_SOURCE_INVALID", f"{source.tags_url}: {malformed}") from None
    return releases_from_tags(names)


def _relative_member(name: str, subdirectory: str) -> tuple[str, ...] | None:
    """Return a member's path inside the source subdirectory, without the archive's top folder."""
    inner = PurePosixPath(name).parts[1:]
    prefix = PurePosixPath(subdirectory).parts if subdirectory else ()
    if tuple(inner[: len(prefix)]) != prefix:
        return None
    return tuple(inner[len(prefix) :])


def _is_wanted(member: tarfile.TarInfo, subdirectory: str) -> bool:
    """Return whether an archive member is engine code or the changelog."""
    relative = _relative_member(member.name, subdirectory)
    return bool(relative) and relative[0] in WANTED_ROOTS


def fetch_release(source: Source, ref: str, destination: Path) -> Path:
    """Download the archive of `ref` and extract its engine and changelog.

    Args:
        source: Where releases come from.
        ref: A release tag or a commit of the canonical repository.
        destination: An empty scratch directory.

    Returns:
        The extracted source subdirectory, holding `engine/` and `CHANGELOG.md`.

    Raises:
        EngineLifecycleError: `ENGINE_ARCHIVE_INVALID` when the archive cannot be
            read, `ENGINE_ARCHIVE_EMPTY` when it holds no engine.
    """
    archive = destination / "release.tar.gz"
    archive.write_bytes(read_url(source.archive_url.format(ref=ref)))
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            members = [member for member in bundle.getmembers() if _is_wanted(member, source.subdirectory)]
            bundle.extractall(destination / "tree", members=members, filter="data")
    except (tarfile.TarError, OSError) as unreadable:
        raise EngineLifecycleError("ENGINE_ARCHIVE_INVALID", f"{ref}: {unreadable}") from None
    if not members:
        raise EngineLifecycleError("ENGINE_ARCHIVE_EMPTY", f"ref={ref} subdirectory={source.subdirectory}")
    top = PurePosixPath(members[0].name).parts[0]
    return destination / "tree" / top / source.subdirectory


__all__ = ["ALLOWED_SCHEMES", "fetch_release", "list_releases", "read_url"]

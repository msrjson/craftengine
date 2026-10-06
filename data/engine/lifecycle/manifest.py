"""File manifests of an engine tree and the drift between two of them.

A manifest maps every engine-relative POSIX path to the SHA-256 of its bytes.
Bytecode caches are not part of a release and never count as drift.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

#: Directory names that hold generated files, never release content.
IGNORED_DIRECTORIES = frozenset({"__pycache__"})

#: File suffixes that are generated, never release content.
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at `path`."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_release_file(relative: Path) -> bool:
    """Return whether an engine-relative path is release content, not a cache."""
    return relative.suffix not in IGNORED_SUFFIXES and IGNORED_DIRECTORIES.isdisjoint(relative.parts)


def build_manifest(engine_dir: Path) -> dict[str, str]:
    """Return the manifest of the engine tree at `engine_dir`.

    Args:
        engine_dir: The `engine/` directory to hash.

    Returns:
        Engine-relative POSIX path to SHA-256, for every release file.
    """
    manifest: dict[str, str] = {}
    for path in sorted(engine_dir.rglob("*")):
        relative = path.relative_to(engine_dir)
        if path.is_file() and is_release_file(relative):
            manifest[relative.as_posix()] = hash_file(path)
    return manifest


@dataclass
class Drift:
    """How an actual tree differs from what was expected.

    Args:
        modified: Paths present in both with different content.
        added: Paths only in the actual tree.
        missing: Paths only in the expected manifest.
    """

    modified: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def paths(self) -> list[str]:
        """Return every drifted path, sorted."""
        return sorted([*self.modified, *self.added, *self.missing])

    def __bool__(self) -> bool:
        return bool(self.modified or self.added or self.missing)


def compare(expected: dict[str, str], actual: dict[str, str]) -> Drift:
    """Return the drift of `actual` against `expected`.

    Args:
        expected: The manifest the tree should match.
        actual: The manifest of the tree as it is.

    Returns:
        The drift; falsy when the trees match.
    """
    return Drift(
        modified=sorted(path for path in expected.keys() & actual.keys() if expected[path] != actual[path]),
        added=sorted(actual.keys() - expected.keys()),
        missing=sorted(expected.keys() - actual.keys()),
    )


def expected_with_patches(manifest: dict[str, str], patched: dict[str, str | None]) -> dict[str, str]:
    """Return the manifest a vendored tree should match once its patches are applied.

    Args:
        manifest: The pinned release's manifest.
        patched: Path to the hash a patch recorded, None for a deletion.

    Returns:
        The effective expected manifest.
    """
    effective = {**manifest, **{path: digest for path, digest in patched.items() if digest is not None}}
    return {path: digest for path, digest in effective.items() if patched.get(path, digest) is not None}


__all__ = ["Drift", "build_manifest", "compare", "expected_with_patches", "hash_file", "is_release_file"]

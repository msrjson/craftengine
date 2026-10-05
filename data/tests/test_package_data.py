"""Every file the engine reads at runtime ships in the installed package.

A template missing from `package-data` is invisible in a source checkout and
breaks every project that installs the framework with pip: v4.4.0 shipped
without `auth_templates/` and `shared_templates/`, so `make auth` and
`make admin` crashed, and an extension template stored as a hidden file was
silently dropped. The CRM demo, which installs the released package, found it.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import fnmatch
import tomllib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"


def _package_data() -> dict[str, list[str]]:
    with open(ROOT / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)["tool"]["setuptools"]["package-data"]


def _shipped(relative: PurePosixPath, package_data: dict[str, list[str]]) -> bool:
    """Return whether a non-Python file under `engine/` matches a package-data glob."""
    for package, patterns in package_data.items():
        package_dir = PurePosixPath(*package.split("."))
        try:
            inner = relative.relative_to(package_dir)
        except ValueError:
            continue
        if any(fnmatch.fnmatch(str(inner), pattern.replace("**/", "*")) for pattern in patterns):
            return True
    return False


def _data_files() -> list[PurePosixPath]:
    return sorted(
        PurePosixPath(path.relative_to(ROOT).as_posix())
        for path in ENGINE.rglob("*")
        if path.is_file() and path.suffix not in {".py", ".pyc"} and "__pycache__" not in path.parts
    )


def test_every_engine_data_file_is_covered_by_package_data():
    package_data = _package_data()
    missing = [str(path) for path in _data_files() if not _shipped(path, package_data)]
    assert missing == []


def test_no_shipped_template_is_a_hidden_file():
    hidden = [str(path) for path in _data_files() if path.name.startswith(".")]
    assert hidden == []

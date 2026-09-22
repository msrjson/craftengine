"""Generation of a new, bare Craft Engine project.

The framework repository used to be the starting point: a developer cloned an
application - admin panel, demo models, theme, documentation site - and had to
work out which parts were the engine and which were a demonstration. Nothing
marked the difference, so an agent asked to start a project either rebuilt
what was already there or grafted its feature onto a layout meant to be
thrown away.

`craft new` replaces that. It writes a project that boots, answers one route,
and contains nothing to reuse. Authentication, the admin panel and CRUD
scaffolding are added on request by `make:auth`, `make:admin` and `make:crud`.

The skeleton lives as real files under `skeleton/`, suffixed `.stub` so the
test collector and the import system ignore them. Copying files is what this
module does; it never builds source code out of strings.
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, Final, List

#: Root of the template tree, alongside this module.
SKELETON_ROOT: Final[str] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skeleton")

#: Suffix marking a template file. Stripped when the file is written out.
STUB_SUFFIX: Final[str] = ".stub"

#: Directories that must exist in a generated project even when no template
#: file lands in them, because the framework writes into them at runtime.
RUNTIME_DIRECTORIES: Final[List[str]] = [
    os.path.join("storage", "logs"),
    os.path.join("storage", "app"),
    os.path.join("storage", "framework", "cache"),
    os.path.join("storage", "framework", "sessions"),
]

#: Package directories that need an `__init__.py` to be importable.
PACKAGE_DIRECTORIES: Final[List[str]] = [
    "app",
    os.path.join("app", "Http"),
    os.path.join("app", "Http", "Controllers"),
    os.path.join("app", "Http", "Middleware"),
    os.path.join("app", "Models"),
    os.path.join("app", "Providers"),
    "bootstrap",
    "database",
    os.path.join("database", "seeders"),
    "routes",
    "tests",
]


class ProjectDirectoryNotEmpty(RuntimeError):
    """Raised when the target directory already holds files.

    A developer-facing failure, never rendered to an end user, so it carries a
    stable code and the offending path rather than a sentence.

    Attributes:
        code: Stable machine code for this failure.
        path: The directory that was not empty.
    """

    code: str = "PROJECT_DIRECTORY_NOT_EMPTY"

    def __init__(self, path: str) -> None:
        super().__init__(self.code)
        self.path = path


def _template_files() -> List[str]:
    """List every template file, as paths relative to the skeleton root.

    Returns:
        Relative paths, sorted so generation order is deterministic.
    """
    found: List[str] = []
    for directory, _, filenames in os.walk(SKELETON_ROOT):
        for filename in filenames:
            if not filename.endswith(STUB_SUFFIX):
                continue
            absolute = os.path.join(directory, filename)
            found.append(os.path.relpath(absolute, SKELETON_ROOT))
    return sorted(found)


def _destination_for(relative_template: str) -> str:
    """Map a template path to its path inside the generated project.

    Args:
        relative_template: Path relative to the skeleton root, ending in the
            stub suffix.

    Returns:
        The same path with the stub suffix removed.
    """
    return relative_template[: -len(STUB_SUFFIX)]


def _write_package_markers(target: str, written: Dict[str, str]) -> None:
    """Create an empty `__init__.py` in each package directory.

    Args:
        target: Root of the generated project.
        written: Accumulator mapping a project-relative path to its absolute
            path; mutated in place.
    """
    for package in PACKAGE_DIRECTORIES:
        directory = os.path.join(target, package)
        os.makedirs(directory, exist_ok=True)
        marker = os.path.join(directory, "__init__.py")
        if os.path.exists(marker):
            continue
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("")
        written[os.path.join(package, "__init__.py")] = marker


def _write_runtime_directories(target: str) -> None:
    """Create the directories the framework writes into at runtime.

    Each gets a `.gitkeep` so the empty directory survives version control.

    Args:
        target: Root of the generated project.
    """
    for runtime in RUNTIME_DIRECTORIES:
        directory = os.path.join(target, runtime)
        os.makedirs(directory, exist_ok=True)
        keep = os.path.join(directory, ".gitkeep")
        if not os.path.exists(keep):
            with open(keep, "w", encoding="utf-8") as handle:
                handle.write("")


def build_project(target_path: str, *, force: bool = False) -> Dict[str, object]:
    """Generate a bare project at `target_path`.

    Args:
        target_path: Directory to generate into. Created when absent.
        force: Generate into a directory that already holds files, overwriting
            any file the skeleton also provides.

    Returns:
        A mapping with `path` (the project root) and `files` (project-relative
        path to absolute path, for every file written).

    Raises:
        ProjectDirectoryNotEmpty: If the target holds files and `force` is
            False.
    """
    target = os.path.abspath(target_path)
    if os.path.isdir(target) and os.listdir(target) and not force:
        raise ProjectDirectoryNotEmpty(target)

    written: Dict[str, str] = {}
    for relative_template in _template_files():
        relative_output = _destination_for(relative_template)
        destination = os.path.join(target, relative_output)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copyfile(os.path.join(SKELETON_ROOT, relative_template), destination)
        written[relative_output] = destination

    _write_package_markers(target, written)
    _write_runtime_directories(target)
    return {"path": target, "files": written}

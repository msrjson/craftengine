"""
Agent catalog: installable development agents, skills and commands.

Category: Core Framework (CLI).
Relations:
  - Invoked from `dev.py agent:list` and `dev.py agent:install` (`engine/cli/app.py`).
  - Installed in full by `dev.py agent:scaffold` (`engine/cli/agent_scaffolder.py`).
  - Ships Markdown definitions under `agents/`, `skills/<name>/`, `commands/`
    and `references/`, declared as package data in `pyproject.toml`.
References:
  - Guide: `documentation/ai_agents.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

CATALOG_ROOT = Path(__file__).resolve().parent

# kind -> directory inside the catalog; the installed layout mirrors it.
KIND_DIRECTORIES: dict[str, str] = {
    "agent": "agents",
    "skill": "skills",
    "command": "commands",
    "reference": "references",
}

DEFAULT_TARGET_DIR = ".agents"


class LegacyAgentDirectoryError(FileExistsError):
    """Raised when a project still carries a physical `.claude/` directory.

    The engine keeps one physical agent directory. A physical `.claude/` is the
    legacy layout; it is refused rather than merged blindly, so the operator
    migrates it and `.claude` becomes a symlink to the single directory.
    """

    code = "AGENT_LEGACY_DIRECTORY"


class UnknownCatalogEntryError(LookupError):
    """Raised when a requested name matches no catalog entry."""

    code = "AGENT_CATALOG_UNKNOWN_ENTRY"

    def __init__(self, names: list[str]) -> None:
        super().__init__(", ".join(names))
        self.names = names


@dataclass(frozen=True)
class CatalogEntry:
    """One installable catalog item.

    Attributes:
        kind: One of the keys of `KIND_DIRECTORIES`.
        name: Kebab-case identifier, unique within its kind.
        description: The `description` frontmatter value, or an empty string.
        source: The Markdown file, or the skill directory, inside the catalog.
    """

    kind: str
    name: str
    description: str
    source: Path

    def destination(self, base_path: Path, target_dir: str = DEFAULT_TARGET_DIR) -> Path:
        """Return where this entry is installed under `base_path`.

        Args:
            base_path: The project root.
            target_dir: The agent configuration directory, relative to `base_path`.

        Returns:
            The file or directory path the entry is copied to.
        """
        return base_path / target_dir / KIND_DIRECTORIES[self.kind] / self.source.name


def _read_description(markdown: Path) -> str:
    """Return the `description:` value from a Markdown frontmatter block."""
    lines = markdown.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            return ""
        if line.startswith("description:"):
            return line.partition(":")[2].strip().strip('"')
    return ""


def _entry_from_path(kind: str, path: Path) -> CatalogEntry | None:
    """Build an entry from a catalog path, or return None if it is not one."""
    if kind == "skill":
        manifest = path / "SKILL.md"
        if not manifest.is_file():
            return None
        return CatalogEntry(kind, path.name, _read_description(manifest), path)
    if path.suffix != ".md":
        return None
    return CatalogEntry(kind, path.stem, _read_description(path), path)


def list_entries(kind: str | None = None) -> list[CatalogEntry]:
    """List the catalog, sorted by kind order and then by name.

    Args:
        kind: Restrict the listing to one kind; None lists every kind.

    Returns:
        The matching entries.

    Raises:
        ValueError: If `kind` is not a known kind.
    """
    if kind is not None and kind not in KIND_DIRECTORIES:
        raise ValueError(kind)
    kinds = [kind] if kind else list(KIND_DIRECTORIES)
    entries: list[CatalogEntry] = []
    for current in kinds:
        directory = CATALOG_ROOT / KIND_DIRECTORIES[current]
        paths = sorted(directory.iterdir()) if directory.is_dir() else []
        entries.extend(e for e in (_entry_from_path(current, p) for p in paths) if e)
    return entries


def _select(names: Iterable[str] | None) -> list[CatalogEntry]:
    """Resolve requested names to entries; None selects the whole catalog."""
    catalog = list_entries()
    if names is None:
        return catalog
    wanted = list(dict.fromkeys(names))
    selected = [entry for entry in catalog if entry.name in wanted and entry.kind != "reference"]
    unknown = [name for name in wanted if name not in {entry.name for entry in selected}]
    if unknown:
        raise UnknownCatalogEntryError(unknown)
    references = [entry for entry in catalog if entry.kind == "reference"]
    return selected + references


def _copy(entry: CatalogEntry, destination: Path) -> None:
    """Copy one entry to its destination, replacing what is there."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if entry.source.is_dir():
        shutil.copytree(entry.source, destination, dirs_exist_ok=True)
        return
    shutil.copyfile(entry.source, destination)


def ensure_layout(base_path: str, target_dir: str = DEFAULT_TARGET_DIR) -> str:
    """Create the single agent directory and keep `.claude` a symlink to it.

    One physical agent directory per project: the catalog lands in `target_dir`
    and `.claude` is a symlink so a harness that insists on that path still
    finds the files. A legacy physical `.claude/` is refused, never merged, so
    the operator migrates it first.

    Args:
        base_path: The project root.
        target_dir: The agent directory, relative to `base_path`.

    Returns:
        The absolute path of the agent directory.

    Raises:
        LegacyAgentDirectoryError: If `.claude` exists as a real directory.
    """
    root = Path(base_path)
    link = root / ".claude"
    legacy = target_dir != ".claude" and link.exists() and not link.is_symlink()
    if legacy:
        raise LegacyAgentDirectoryError(
            f"{link} is a physical directory; this project keeps its agent files in "
            f"{target_dir}. Move the contents of {link} into {target_dir}, then replace "
            f"{link} with a symlink to {target_dir} and run the command again."
        )
    target = root / target_dir
    target.mkdir(parents=True, exist_ok=True)
    if target_dir != ".claude" and not link.is_symlink():
        try:
            link.symlink_to(target_dir, target_is_directory=True)
        except OSError:
            # Filesystems without symlink support still get the catalog in
            # `target_dir`; only the `.claude` convenience link is skipped.
            pass
    return str(target)


def install(
    base_path: str,
    names: Iterable[str] | None = None,
    force: bool = False,
    target_dir: str = DEFAULT_TARGET_DIR,
) -> dict[str, list[str]]:
    """Install catalog entries into a project's agent configuration directory.

    Shared references are always installed with any selection, because the
    agents and skills link to them. Conflicts are checked before anything is
    written, so a refused install leaves the project untouched. The layout is
    fixed first (`ensure_layout`): `.claude` becomes a symlink to the single
    agent directory, and a legacy physical `.claude/` is refused.

    Args:
        base_path: The project root.
        names: Entry names to install; None installs the whole catalog.
        force: Overwrite entries that already exist.
        target_dir: The agent configuration directory, relative to `base_path`.

    Returns:
        Installed paths grouped by kind.

    Raises:
        UnknownCatalogEntryError: If a name matches no agent, skill or command.
        FileExistsError: If an entry already exists and `force` is False, or if a
            legacy physical `.claude/` directory is present.
    """
    root = Path(base_path)
    selected = _select(names)
    planned = [(entry, entry.destination(root, target_dir)) for entry in selected]
    existing = [str(path) for entry, path in planned if path.exists() and entry.kind != "reference"]
    if existing and not force:
        raise FileExistsError(existing[0])
    ensure_layout(base_path, target_dir)
    installed: dict[str, list[str]] = {kind: [] for kind in KIND_DIRECTORIES}
    for entry, destination in planned:
        _copy(entry, destination)
        installed[entry.kind].append(str(destination))
    return installed

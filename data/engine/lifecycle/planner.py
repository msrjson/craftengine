"""What happens to each local patch when a vendored engine moves to another release.

For every patched file, three hashes decide:

| Target release vs patch          | Outcome                                       |
|----------------------------------|-----------------------------------------------|
| target equals the patched content| absorbed upstream: the path leaves the patch  |
| target equals the pinned release | untouched upstream: the patch is carried over |
| anything else                    | both sides changed: a conflict blocks the move|

A patch whose every path was absorbed is retired. A patch the owner drops on
the command line is retired too: the upstream file wins.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from dataclasses import dataclass, field, replace

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import EngineLock, Patch


@dataclass
class MovePlan:
    """The patch outcome of a move.

    Args:
        carried: Patches re-applied on the target, trimmed to the paths still needed.
        retired: Ids of patches the target absorbed or the owner dropped.
        conflicts: Patch id to the paths both sides changed.
    """

    carried: list[Patch] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)


def _classify(path: str, digest: str | None, pinned: dict[str, str], target: dict[str, str]) -> str:
    """Return `absorbed`, `carried` or `conflict` for one patched path."""
    if target.get(path) == digest:
        return "absorbed"
    if target.get(path) == pinned.get(path):
        return "carried"
    return "conflict"


def plan_move(patches: list[Patch], pinned: dict[str, str], target: dict[str, str], dropped: set[str]) -> MovePlan:
    """Decide what each patch becomes on the target release.

    Args:
        patches: The project's registered patches.
        pinned: Manifest of the release the project is pinned to.
        target: Manifest of the release it moves to.
        dropped: Patch ids the owner discards in favor of upstream.

    Returns:
        The plan; a move is allowed only when `conflicts` is empty.
    """
    plan = MovePlan()
    for patch in patches:
        if patch.id in dropped:
            plan.retired.append(patch.id)
            continue
        outcomes = {path: _classify(path, digest, pinned, target) for path, digest in patch.files.items()}
        conflicting = sorted(path for path, outcome in outcomes.items() if outcome == "conflict")
        kept = {path: patch.files[path] for path, outcome in outcomes.items() if outcome == "carried"}
        if conflicting:
            plan.conflicts[patch.id] = conflicting
        elif kept:
            plan.carried.append(replace(patch, files=kept))
        else:
            plan.retired.append(patch.id)
    return plan


def checked_plan(lock: EngineLock, manifest: dict[str, str], dropped: set[str]) -> MovePlan:
    """Plan the patches and refuse the move on any conflict.

    Args:
        lock: The project's lock (its patches and pinned manifest).
        manifest: Manifest of the target release.
        dropped: Patch ids the owner discards in favor of upstream.

    Returns:
        A plan without conflicts.

    Raises:
        EngineLifecycleError: `ENGINE_PATCH_CONFLICT` naming each patch and path.
    """
    plan = plan_move(lock.patches, lock.manifest, manifest, dropped)
    if plan.conflicts:
        detail = ";".join(f"{patch_id}:{','.join(paths)}" for patch_id, paths in sorted(plan.conflicts.items()))
        raise EngineLifecycleError("ENGINE_PATCH_CONFLICT", detail)
    return plan


__all__ = ["MovePlan", "checked_plan", "plan_move"]

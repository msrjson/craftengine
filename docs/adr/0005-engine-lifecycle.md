# ADR 0005 — Engine lifecycle: pin, update, upgrade and hotfix

- **Status:** accepted (owner, 2026-10-06)
- **Date:** 2026-10-06
- **Follows:** ADR 0001, ADR 0003
- **Scope:** how a project built on Craft Engine knows which engine it runs,
  moves to a newer release, and takes a single fix without moving

## Context

Nothing recorded which engine a project runs. `craft new` copied the skeleton
and wrote no pin. The CRM demo pins a tag archive in its Dockerfile by hand.
SoftPax vendors `engine/` and has drifted from the release it came from, with
314 files that differ from v4.4.2, and had begun building its own lock and
patch ledger before it could upgrade. Without a lifecycle in the engine,
every project invents one, and no project can tell a deliberate local fix
from accidental drift.

## Decision

1. **One lock per project.** `craft-engine.lock` (JSON, at the project root)
   records the release tag (`vMAJOR.MINOR.PATCH-rNNNNN`, NR-01), its version
   and counter, the source, and the mode:
   - `package`: the engine is installed from a pinned archive. The lock lists
     the project files that spell the ref (`pin_files`).
   - `vendored`: the engine is a directory committed with the project. The
     lock holds the SHA-256 manifest of the pinned release's `engine/` and
     every local patch.
2. **Local changes are patches or drift.** A patch has an id, a class
   (`security`, `improvement`, `upstream-sync`), a reason, an author and the
   hash of each file it changes. A vendored file that differs from the release
   and is covered by no patch is unregistered drift. `status` exits 1 when
   there is drift, and every move refuses while any remains.
3. **Commands.** `craft engine adopt | status | patch | hotfix | update | upgrade`.
   - `update` moves to the newest release on the same `major.minor` line.
   - `upgrade --to X.Y.Z` moves across minors and majors and refuses the same
     or an older version.
   - `hotfix <ref> <paths>` takes files from a canonical tag or commit into the
     vendored engine and records them as a `security` patch without moving
     the pin.
4. **Patches across a move.** For each patched file: if the target equals the
   patched content, the patch was absorbed upstream and is retired. If the
   target equals the pinned release, the patch is carried over. Otherwise both
   sides changed and the move is refused (`ENGINE_PATCH_CONFLICT`) until the
   owner drops the patch with `--drop-patch` or re-records it on the new base.
5. **Transactional apply.** A vendored move stages the target beside the
   current engine, swaps it in with two renames on the same filesystem, runs
   the optional `--verify` command, and renames the previous engine back if
   that command fails. A package move rewrites the pin files and restores them
   on failure. The lock is written atomically, and only after verification
   passes.
6. **Source.** Releases are tag archives of the canonical repository, read with
   the standard library (`urllib`, `tarfile` with the `data` filter). Only
   `https` and `file` URLs are accepted. There is no dependency on git, which
   the application container does not have. The development workspace is
   never a source (owner ruling 2026-09-22).
7. **Panel and console are one service.** `EngineUpdates` (container key
   `engine_updates`) caches the update notice that `engine check` produces,
   and reviews and applies moves. The admin panel screen (`make:engine-panel`,
   included in `make:admin`) and the console both call it. A panel request
   never calls the network, except the explicit "check" action. Moves run only
   the verification command recorded in the lock, never one from a request,
   and one at a time per project.
8. **Database is out of scope.** Engine migrations run forward-only through
   `migrate` after a move, as they always have (NR-02). There is no schema
   rollback.

## Consequences

- `craft new` writes a `package` lock for the release that generated it.
- A vendored project adopts once (`adopt <tag> --mode vendored`) and then
  registers its existing edits with `patch` until `status` is clean. That is
  the path for SoftPax's 314 differing files.
- Upgrade notes come from the target release's `CHANGELOG.md`. The `Removed`,
  `Deprecated`, `Security` and `Changed` entries are printed for review, so the
  changelog categories (NR-04) are now part of the upgrade contract.
- The lifecycle lives in `engine/lifecycle/` and carries no business rule
  (EB-01). It never imports the application (EB-02).

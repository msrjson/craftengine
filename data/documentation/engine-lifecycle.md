# Engine lifecycle: update, upgrade and hotfix

A Craft project records the engine release it runs in `craft-engine.lock`. The
`engine` commands read that lock to report drift, move to a newer release, or
take a single fix without moving. The design is in ADR 0005.

## Modes

| Mode | The engine reaches the project as | What a move changes |
|---|---|---|
| `package` | an archive installed from a pinned tag (Dockerfile, requirements) | the ref in each pin file |
| `vendored` | an `engine/` directory committed with the project | the files of `engine/` |

`craft new` writes a `package` lock for the release that generated the project.

## Adopting a release

```bash
# Package mode: list the files that spell the ref
python dev.py engine adopt v4.4.2-r00024 --pin Dockerfile

# Vendored mode: the release manifest is downloaded and recorded
python dev.py engine adopt v4.4.2-r00024 --mode vendored --engine-path engine
```

`--archive-url`, `--tags-url` and `--subdirectory` point at a mirror (an
`https://` or `file://` URL) for air-gapped hosts. By default they point at
the canonical repository.

## Status

```bash
python dev.py engine status            # pin, patches, drift, newer releases
python dev.py engine status --offline  # skip the release listing
```

`status` exits 1 when a vendored engine has **unregistered drift**: a file that
differs from the pinned release and is covered by no patch.

## Patches

Every deliberate local change to a vendored engine is a patch: an id, a class
(`security`, `improvement`, `upstream-sync`), a reason and an author.

```bash
python dev.py engine patch http/response.py --id SP-660 --class improvement \
  --reason "keep the proxy host" --by claude
```

## Hotfix

A hotfix takes files from a canonical tag or commit and records them as a
`security` patch. The pin does not move.

```bash
python dev.py engine hotfix v4.4.3-r00025 http/response.py --id GHSA-xxxx \
  --reason "header injection" --by owner
```

A hotfix refuses a path that has unregistered local edits, so it never
overwrites work it cannot see.

## Update and upgrade

```bash
python dev.py engine update --dry-run                        # plan and notes only
python dev.py engine update --verify "python -m pytest tests -q"
python dev.py engine upgrade --to 4.5.0 --verify "python -m pytest tests -q"
```

- `update` moves to the newest release of the same `major.minor` line.
- `upgrade` moves across minors and majors. It refuses the same or an older
  version, and prints the changelog entries under `Removed`, `Deprecated`,
  `Security` and `Changed` for every release it crosses.
- Any unregistered drift blocks the move.
- Patches whose content the target already contains are retired. Patches on
  files the target did not touch are carried over. A patch on a file both
  sides changed blocks the move (`ENGINE_PATCH_CONFLICT`) until you pass
  `--drop-patch <id>` (upstream wins) or re-record the patch on the new base.
- The move is transactional. The new engine is staged beside the current one
  and swapped in, then `--verify` runs. If verification fails, the previous
  engine (or the previous pin files) is restored and the lock is left as it was.

After a move, rebuild or reinstall the engine where it is packaged, then run
`python dev.py migrate`. Engine migrations only go forward. There is no schema
rollback.

## Checking for updates

`engine check` asks the canonical repository for newer releases and caches the
answer as the **update notice**. The panel reads only that cache, so a page
never waits on the network. Schedule the check in `routes/console.py`:

```python
Schedule.command("engine check").cron("0 */6 * * *")
```

## The verification command

Every move runs the command recorded in the lock after the swap, and rolls
back if it fails. Set it once from the console, and the panel uses the same
command:

```bash
python dev.py engine verify-command "python -m pytest tests -q"
python dev.py engine verify-command ""        # clear it
```

`--verify` on `update` and `upgrade` overrides it for one run. The panel never
accepts a command from a form. If it did, every admin could run any command
on the server.

## Updating from the admin panel

`make:admin` generates the **Engine updates** screen at `/admin/engine`. An
existing panel gets it with:

```bash
python dev.py make:engine-panel
python dev.py migrate          # seeds the screen's translations (en, pt-BR, es)
```

| Panel action | Console equivalent |
|---|---|
| The alert on the panel pages ("a new release is available") | `engine check` (scheduled) |
| **Check for updates** | `engine check` |
| Overview: pin, running engine, verification command, patches, drift | `engine status --offline` |
| **Review update / upgrade**: patches and changelog, nothing changed | `engine update --dry-run`, `engine upgrade --to X.Y.Z --dry-run` |
| **Apply** | `engine update`, `engine upgrade --to X.Y.Z` |

Every route requires `auth` and `role:admin`. The two state-changing actions are
POST forms with `@csrf`. Only one move runs at a time per project: a second
request is refused with `ENGINE_MOVE_IN_PROGRESS`. Each applied move is logged
as `engine_lifecycle_moved`, with the admin's e-mail and both refs.

Panels generated before this screen do not show the alert on their other
pages. To add it, put the `engine_update` notice in the context in
`PanelPage.panel()` (see the current `make:admin` template), then add
`@include("partials.engine_update_alert")` to the top of each page's content
section.

## Refusal codes

| Code | Meaning |
|---|---|
| `ENGINE_LOCK_MISSING` / `ENGINE_LOCK_INVALID` / `ENGINE_LOCK_EXISTS` | no lock, unreadable lock, or a lock already present (`--force`) |
| `ENGINE_REF_INVALID` / `ENGINE_VERSION_INVALID` / `ENGINE_MODE_INVALID` | the input is not a release tag, a version or a mode |
| `ENGINE_SOURCE_SCHEME_REFUSED` / `ENGINE_SOURCE_UNREACHABLE` / `ENGINE_SOURCE_INVALID` | the source cannot be read |
| `ENGINE_ARCHIVE_INVALID` / `ENGINE_ARCHIVE_EMPTY` | the archive is unreadable or holds no engine |
| `ENGINE_DRIFT_UNREGISTERED` | local edits not covered by a patch |
| `ENGINE_NOT_VENDORED` | patch and hotfix need a vendored engine |
| `ENGINE_PATCH_CLASS_INVALID` / `ENGINE_PATCH_EXISTS` / `ENGINE_PATCH_EMPTY` | bad class, id in use, or nothing changed |
| `ENGINE_HOTFIX_PATH_MISSING` / `ENGINE_HOTFIX_NO_CHANGE` | the ref lacks the file, or it equals the pinned release |
| `ENGINE_ALREADY_LATEST` / `ENGINE_NOT_NEWER` / `ENGINE_RELEASE_NOT_FOUND` | no target to move to |
| `ENGINE_PATCH_CONFLICT` | both the patch and the target changed a file |
| `ENGINE_PIN_NOT_FOUND` | a pin file is missing or no longer spells the pinned ref |
| `ENGINE_VERIFY_FAILED` | the verification command failed; the move was rolled back |
| `ENGINE_MOVE_IN_PROGRESS` | another move is running in this project |

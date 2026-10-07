---
name: do-app-isolation
description: Rules and procedure for touching DigitalOcean App Platform from a workspace. Use before creating, updating, deploying or inspecting any DigitalOcean app, before reading a DigitalOcean token, or when the owner says "subir na digital ocean", "deploy no DO", "criar app na DO". Each workspace manages only the one app bound to it; every other app in the account is off limits.
---
<!-- version: 1.2.0 | build: 2026-09-18 | update: 2026-09-18 -->

# DigitalOcean app isolation

## Why this exists

A DigitalOcean API token is **account-wide**. Custom scopes narrow it by
resource *type* (`app:read`, `app:update`, …), never by resource *id*: a token
that can update this site can update, redeploy or delete every other app in the
account — including production apps of other workspaces. The API will not stop
a mistake, so the workspace must.

## Rules — unconditional

1. **One workspace, one app.** A workspace touches only the app recorded in its
   own `.claude/do-app.json` (`app_name` + `app_id`). Any other app is read-only
   at most, and only its name, to avoid a collision on create.
   The app lives in the owner's DigitalOcean project
   (`c87eafe0-7bb4-45ee-996c-71874b62758d`, pinned as `PROJECT_ID` in the
   wrapper); the wrapper creates it there and refuses to act on it if it is
   ever moved out. Sharing a project with other apps grants nothing: the
   binding is per app, not per project.
2. **Only through the wrapper.** All App Platform calls go through
   `.claude/scripts/do-app.py`. No `doctl`, no hand-written `curl` with the
   token, no app id typed on a command line.
3. **Never delete.** The wrapper has no delete. Deleting an app — this one or
   any other — is done by the owner in the control panel.
4. **Never rebind.** Do not edit `.claude/do-app.json` to point at another app,
   and do not rename the app in `deploy/do-app.yaml`; the wrapper refuses both.
5. **The token never moves.** It stays in the gitignored `.do/` directory (`.do/dotoken.txt`) (or
   `DIGITALOCEAN_TOKEN`). Never print it, commit it, copy it to another
   workspace, put it in a handoff, or let it into a Docker image
   (`.dockerignore` excludes `.do/`).
6. **Other workspaces are not yours.** If another workspace's app needs a
   change, write a handoff to that workspace (global `AGENTS.md` §0.2). Never
   reuse this token or this wrapper for it.

## Procedure

```bash
python3 .claude/scripts/do-app.py propose   # validate deploy/do-app.yaml, creates nothing
python3 .claude/scripts/do-app.py create    # once; writes .claude/do-app.json
python3 .claude/scripts/do-app.py status    # id, name, live URL, deployment phase
python3 .claude/scripts/do-app.py update    # apply deploy/do-app.yaml to the bound app
python3 .claude/scripts/do-app.py deploy    # force a rebuild of the bound app
```

Commit `.claude/do-app.json` after `create`: the app id is not a secret, and
the binding is what makes rule 1 checkable by the next agent.

## Porting to another workspace

Copy this skill and the wrapper **from inside that workspace's own session**,
change `deploy/do-app.yaml`, and give it its **own token** with the smallest
custom scope that works (`app:create`, `app:read`, `app:update`; no `delete`,
no droplet, database or DNS scopes). Separate tokens mean a leak in one
workspace can be revoked without touching the others.

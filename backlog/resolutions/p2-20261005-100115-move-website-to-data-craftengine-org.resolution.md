---
task: p2-20261005-100115-move-website-to-data-craftengine-org
outcome: resolved
agent: claude@claude-code
started_at: 2026-10-05T12:30:00Z
finished_at: 2026-10-05T10:30:44Z
---

## What changed

- The site repository (`msrjson/craftengine.org`, its own Git repository) moved from `website/` to `data-website/` with a plain `mv`: its history, remote and the uncommitted `site.json` edit found in it were preserved untouched.
- `.gitignore`: `website/` -> `data-website/`, plus `data-demo/` (the demo is its own repository too, owner ruling 2026-10-05: three contexts never mixed).
- `docker-compose.yml`: the `website` service builds `./data-website`; the header documents the three contexts.
- Open tasks that named `website/` paths were updated with a History line.
- The DigitalOcean app builds `/` from the GitHub repository, not from a local path: its spec (`deploy/do-app.yaml`) is unchanged and no deploy was triggered.

## Verification

```bash
cd data-website && git status --short && git log --oneline -1   # M site.json; 2672dcc (same as before the move)
docker compose config --quiet                                   # exit 0
git check-ignore data-website data-demo                         # both ignored
```

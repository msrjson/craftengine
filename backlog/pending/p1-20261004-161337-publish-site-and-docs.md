---
id: "20261004-161337"
title: Publish the proxy section, refreshed test results and fixed docs on craftengine.org
type: chore
priority: 1
autonomous: false
blocked_by: owner-action
max_attempts: 2
attempts: 0
created_at: 2026-10-04T16:13:37Z
updated_at: 2026-10-04T16:13:37Z
source: evaluation of the boundary/proxy release, 2026-10-04
touches: []
---

## Problem

craftengine.org still shows v4.1.0 test results and has no internal proxy section; /docs still publishes broken tables and no benchmark. The changes are committed locally only: framework `a65e45c` (docs build and guide) and site `44c92d4` in `website/` (proxy section, `sync_benchmark.py`, test facts from JUnit at `4b9d3a6`).

## Evidence

- `website/` commit `44c92d4`: proxy section in en/pt-BR/es, facts from `.claude/reports/20261004-internal-proxy-benchmark.json`.
- The landing links `commit 4b9d3a6` and `benchmark at commit 480dd2b` return 404 until the framework is pushed.
- The DigitalOcean CDN caches `/assets/*` for a day; `build.py` fingerprints them.

## Done when

- [ ] Framework `master` pushed (the /docs component builds from it).
- [ ] `website/` `main` pushed.
- [ ] Deployment of the bound app is ACTIVE with the site commit hash, checked through `.claude/scripts/do-app.py`.
- [ ] `/#proxy`, `/pt-BR/#proxy`, `/es/#proxy` and `/docs/internal-proxy.html#benchmark-before-and-after` render on the default ingress.

## Verify

```bash
python .claude/scripts/do-app.py  # bound_app() / deployments, never another app
```

## Notes

Deploy only the app bound in `.claude/do-app.json` (skill do-app-isolation). Push and deploy need the owner's go-ahead.

## History

- 2026-10-04T16:13:37Z created by claude (source: evaluation of the boundary/proxy release, 2026-10-04)

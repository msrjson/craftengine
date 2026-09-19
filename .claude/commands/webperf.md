---
description: Run a web performance audit of a Craft web surface through the web-performance-auditor agent
argument-hint: [page URL, route pattern, template path, or diff range]
---

`/webperf` targets browser-facing surfaces of a Craft application: Forge-rendered pages, their static assets under `public/`, and the routes that serve them. Do not use it for plugins, CLI commands, queue-only workers or libraries with no browser output; use the `performance-optimization` skill (`.claude/skills/performance-optimization/SKILL.md`) directly for those.

Target: $ARGUMENTS

## Determine the mode

**Deep mode**: activate when any of these is available:

- A Lighthouse JSON report (exported from the Chrome DevTools Lighthouse panel, or produced by the Lighthouse CLI on a developer machine)
- A PageSpeed Insights JSON response (Lighthouse lab data plus CrUX field data)
- A CrUX API response (the user runs it with their own API key; never paste the key into the conversation)
- A DevTools performance trace export
- A live local URL (for example `http://127.0.0.1:9000/...` from `python dev.py serve`) plus the chrome-devtools MCP server configured in the harness, so the agent captures a Lighthouse audit and performance traces itself
- Server-side measurements: a `/metrics` scrape showing `craft_request_duration_seconds` for the route and `craft_db_pool_connections`, `EXPLAIN (ANALYZE, BUFFERS)` output, or `pg_stat_statements` rows from a non-production database

**Quick mode**: the default when none of the above exist. The agent scans templates in `resources/views`, static files in `public/`, controllers, repositories, migrations and config for structural anti-patterns, and labels every finding `potential impact`.

## Gather the inputs

Before spawning the agent, collect without modifying anything:

1. The files in scope: the Forge templates, the layout they extend, the scripts and stylesheets they include, and the controller and repository behind the route. `python dev.py route:list` maps a URL to its controller.
2. For a diff, the changed files from `git diff --name-only <range>`.
3. Any artifact paths or pasted JSON the user supplied.
4. Relevant configuration: `CACHE_DRIVER`, `QUEUE_CONNECTION`, `DB_POOL_SIZE`, `DB_POOL_TIMEOUT` (names only and non-secret values; never copy credentials or tokens).

## Run the audit

Spawn the `web-performance-auditor` agent (`.claude/agents/web-performance-auditor.md`). Pass it explicitly:

- The files, templates, routes or diff under review
- Every artifact path or pasted JSON content
- The target URL or page name when known
- The mode you expect (Quick or Deep), so the agent reports missing inputs if Deep was intended

The agent is read-only. It must not run destructive database commands, write data, or install anything.

The agent returns a scorecard populated only with sourced values, findings ranked by severity, positive observations and proactive recommendations.

## Output

Return the full audit report to the user unchanged. No synthesis or merge step is needed: this is a single-agent command. If the report contains a Critical cache-key or data-exposure finding, add one line recommending a `security-auditor` pass. Fixes are made afterwards with the `performance-optimization` skill and verified in the browser with the `browser-testing-with-devtools` skill (`.claude/skills/browser-testing-with-devtools/SKILL.md`); each kept fix gets its `CHANGELOG.md` entry under `## [Unreleased]`.

---
name: ci-cd-and-automation
description: Builds and maintains CI/CD pipelines that enforce Craft quality gates and release invariants on every change. Use when setting up or modifying build and deployment pipelines, automating quality gates, configuring pytest against SQLite and PostgreSQL in CI, debugging CI failures, or designing deployment and rollback strategies.
---

# CI/CD and Automation

## Overview

Automate the quality gates so that no change reaches production without passing tests, lint,
the governance gates and a production build. CI is the enforcement mechanism for every other
skill: it catches what humans and agents miss, and it does so identically on every change.

**Shift left.** Catch problems as early as possible. A lint failure costs seconds; the same
defect found in production costs hours and maybe data. Order checks from cheapest to most
expensive: static analysis, then governance gates, then unit tests, then database-backed
tests, then the image build, then deployment.

**Faster is safer.** Small batches released often reduce risk. A deploy with three changes is
easy to diagnose; one with thirty is archaeology. Frequent releases also keep the release
process itself exercised and trustworthy.

In Craft, CI also guards the release non-regression laws: the version in `pyproject.toml`
and `engine/__init__.py` agrees, the `rNNNNN` counter is well formed, the changelog carries
the release and an `[Unreleased]` section, destructive database commands are not relied on,
and public facades keep their container accessors.

## When to Use

- Setting up a new project's pipeline
- Adding or modifying automated checks
- Configuring deployment or release pipelines
- When a change should trigger automated verification it does not yet get
- Debugging CI failures
- When the pipeline got slow enough that people started skipping it

## The Quality Gate Pipeline

Every change passes these gates before merge:

```
Pull request opened
    │
    ▼
  LINT              ruff check
    ↓ pass
  TYPES             mypy (where the project enforces it)
    ↓ pass
  LANGUAGE GATE     lint_language.py
    ↓ pass
  STRUCTURE GATE    lint_structure.py
    ↓ pass
  UNIT + FEATURE    python -m pytest tests (SQLite)
    ↓ pass
  NON-REGRESSION    tests/test_release_non_regression.py
    ↓ pass
  INTEGRATION       pytest against PostgreSQL
    ↓ pass
  DEPENDENCY AUDIT  pip-audit
    ↓ pass
  BUILD             production Docker image
    │
    ▼
  Ready for review
```

**No gate can be skipped.** If lint fails, fix the code, not the rule. If a test fails, fix
the behavior, not the assertion. If `lint_language.py` flags a hardcoded string, extract a
translation key with `en`, `pt-BR` and `es` rows — never add an exemption to get green.
Weakening a gate to pass is the one thing that is never the fix.

## GitHub Actions Configuration

### Basic Quality Pipeline

Craft is pure Python 3.14: no Node toolchain, no npm install step, no frontend build. The
whole pipeline is Python plus the database service.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint
        run: ruff check .

      - name: Language standard
        run: python .claude/rules/lint_language.py --format github

      - name: Structure standard
        run: python .claude/rules/lint_structure.py

      - name: Tests (SQLite, with coverage)
        run: python -m pytest tests --cov=app --cov-report=term-missing

      - name: Release non-regression
        run: python -m pytest tests/test_release_non_regression.py

      - name: Dependency audit
        run: |
          pip install pip-audit
          pip-audit
```

Adjust `--cov` to the package under test (`engine` in the framework repository, `app` in an
application). If the repository keeps the language gate under `tools/` with a separate config
for Forge views, run each configuration as its own step so both are blocking.

### With PostgreSQL Integration Tests

SQLite is the fast default for the suite; PostgreSQL is what production runs. Run the same
suite against both, and pin the database image to the version production uses — on an older
server, version-gated tests skip rather than fail, so a mismatch reports green while never
exercising the feature.

```yaml
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: craft_ci
          POSTGRES_USER: craft_ci
          POSTGRES_PASSWORD: ${{ secrets.CI_DB_PASSWORD }}
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U craft_ci"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Apply migrations (forward only)
        run: python dev.py migrate
        env: &pg_env
          DB_HOST: 127.0.0.1
          DB_PORT: "5432"
          DB_DATABASE: craft_ci
          DB_USERNAME: craft_ci
          DB_PASSWORD: ${{ secrets.CI_DB_PASSWORD }}
      - name: Migration status
        run: python dev.py migrate:status
        env: *pg_env
      - name: Integration tests (PostgreSQL)
        run: python -m pytest tests
        env:
          <<: *pg_env
          CRAFT_TEST_DB: pgsql
```

> Even for a throwaway CI database, keep the password in GitHub Secrets rather than inline in
> the workflow. It builds the right habit and stops a CI credential from being copied into a
> real environment. If the repository's workflow still hardcodes one, moving it to a secret is
> a small `ci:` change worth making.

Never use `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop` in any
pipeline, including CI. The service container starts empty on every run, so forward
migrations are all a job ever needs — and a pipeline that exercises only forward migrations
is the pipeline that proves production can be upgraded.

### Browser and End-to-End Checks

For server-rendered Forge pages, most behavior is covered by HTTP feature tests in pytest.
When a flow genuinely needs a real browser (vanilla JS interactions, focus management,
accessibility), run it as a separate job so a slow browser run never blocks the fast gates,
and upload the report on failure:

```yaml
  e2e:
    runs-on: ubuntu-latest
    needs: [quality]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: Start the application
        run: python dev.py serve &
      - name: Wait for readiness
        run: |
          for attempt in $(seq 1 30); do
            curl -fsS http://127.0.0.1:9000/ready && exit 0
            sleep 1
          done
          exit 1
      - name: Browser tests
        run: python -m pytest tests/browser
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: browser-report
          path: tests/browser/report/
```

Check the port and the readiness path against the project's configuration before copying
this: the health routes default to `/health` (liveness) and `/ready` (readiness) and are
configurable. See the `browser-testing-with-devtools` skill
(`.claude/skills/browser-testing-with-devtools/SKILL.md`).

### Production Image Build

Build the production image on every change, after the tests pass, even when nothing is
pushed. A Dockerfile that only gets built at release time breaks at release time.

```yaml
  docker-build:
    needs: [quality, integration]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile.prod
          push: false
          tags: app:${{ github.sha }}
```

### Release Job — Enforce the Version Invariants

A release job derives the tag from the files and refuses to cut one when they disagree. The
scheme is `vX.Y.Z-rNNNNN`; reading only the semantic version silently produces tags without
the counter, which is exactly the drift the non-regression laws exist to prevent.

```yaml
  release:
    needs: [quality, integration, docker-build]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Resolve and verify version
        id: version
        run: |
          VERSION=$(grep -m1 '^version =' pyproject.toml | cut -d'"' -f2)
          INIT_VERSION=$(grep -m1 '^__version__' engine/__init__.py | cut -d'"' -f2)
          RELEASE=$(grep -m1 '^__release__' engine/__init__.py | cut -d'"' -f2)

          if [ "$VERSION" != "$INIT_VERSION" ]; then
            echo "::error::pyproject.toml says ${VERSION}, engine/__init__.py says ${INIT_VERSION}"
            exit 1
          fi
          if ! echo "$RELEASE" | grep -Eq '^r[0-9]{5}$'; then
            echo "::error::__release__ '${RELEASE}' does not match rNNNNN"
            exit 1
          fi
          if ! grep -q "^## \[${VERSION}\] ${RELEASE}" CHANGELOG.md; then
            echo "::error::CHANGELOG.md has no '## [${VERSION}] ${RELEASE}' heading"
            exit 1
          fi
          echo "tag=v${VERSION}-${RELEASE}" >> "$GITHUB_OUTPUT"

      - name: Refuse to reuse an existing tag
        run: |
          if git rev-parse "${{ steps.version.outputs.tag }}" >/dev/null 2>&1; then
            echo "Tag already exists; nothing to release."
            exit 0
          fi
          git tag -a "${{ steps.version.outputs.tag }}" -m "Release ${{ steps.version.outputs.tag }}"
          git push origin "${{ steps.version.outputs.tag }}"
```

Adjust the paths when the package lives in a subdirectory (a `data/` root, for example, uses
`working-directory` on each step or prefixes the file paths). Checking that the counter is
exactly the previous tag's counter plus one is a worthwhile extra step: list tags matching
`v*-r*`, take the highest counter, and compare.

## Feeding CI Failures Back to Agents

The value of CI for an agent is the feedback loop. When CI fails:

```
CI fails
    │
    ▼
Copy the specific failure output (the failing step, not the whole log)
    │
    ▼
Hand it to the agent:
"The CI pipeline failed at <step> with:
<exact error>
Reproduce it locally, fix the cause, run the same command, then push."
    │
    ▼
Agent reproduces -> fixes -> re-runs locally -> pushes -> CI runs again
```

**Key patterns:**

| Failure | Response |
|---|---|
| `ruff check` | Run `ruff check --fix` for safe autofixes, fix the rest by hand, re-run |
| `lint_language.py` | Rename to English, move copy into translation keys with all three locale rows — never exempt |
| `lint_structure.py` | Split the controller, action or function that broke the cap; move SQL into a repository |
| Type error (mypy) | Read the reported location, fix the annotation or the code, never add `Any` to silence it |
| Test failure | Follow the `debugging-and-error-recovery` skill (`.claude/skills/debugging-and-error-recovery/SKILL.md`) |
| Passes on SQLite, fails on PostgreSQL | Dialect difference: types, ordering without `ORDER BY`, case sensitivity, transactional DDL |
| Non-regression test | Sync `pyproject.toml` and `engine/__init__.py`, fix the counter or the changelog heading |
| Image build | Check `Dockerfile.prod`, the dependency pins and files excluded by `.dockerignore` |

## Deployment Strategies

### Preview or Staging Deployments

Every change that alters user-visible behavior should be exercised in an environment that is
not production before it reaches production. Where the hosting platform supports per-branch
preview environments, deploy one per pull request; otherwise keep a single staging
environment that auto-deploys from the default branch.

```yaml
  deploy-staging:
    needs: [docker-build]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy image to staging
        run: ./deploy/deploy.sh staging "${{ github.sha }}"
        env:
          DEPLOY_TOKEN: ${{ secrets.STAGING_DEPLOY_TOKEN }}
```

The deploy script is project-owned. It should push the image, run `python dev.py migrate`
(forward only), switch traffic, and poll `/ready` before declaring success.

### Feature Flags

Feature flags decouple deploying code from releasing behavior. Merge incomplete or risky work
behind a flag so you can:

- **Ship code without enabling it.** Merge early, enable when ready.
- **Roll back without redeploying.** Turn the flag off instead of reverting.
- **Canary.** Enable for 1% of users or one tenant, then 10%, then everyone.
- **Compare.** Measure the flow with and without the feature.

The framework does not ship a flag service, so keep the check behind one small, injectable
plugin rather than scattering configuration reads through controllers:

```python
"""Feature flag lookup, resolved from the container."""

from dataclasses import dataclass
from typing import Protocol


class FeatureFlags(Protocol):
    """Answers whether a named feature is enabled for a subject."""

    def is_enabled(self, feature: str, *, tenant_id: int | None = None) -> bool:
        """Return True when `feature` is on for the tenant (or globally)."""


@dataclass(frozen=True)
class ConfigFeatureFlags:
    """Flags read from configuration, with an optional per-tenant allowlist.

    Args:
        settings: Mapping of feature name to either a bool or a list of tenant ids.
    """

    settings: dict[str, bool | list[int]]

    def is_enabled(self, feature: str, *, tenant_id: int | None = None) -> bool:
        """Return True when the feature is globally on or the tenant is allowlisted.

        Args:
            feature: Flag name, for example "checkout.new_flow".
            tenant_id: Tenant being served, when the flag is tenant-scoped.

        Returns:
            Whether the feature is enabled.
        """
        value = self.settings.get(feature, False)
        if isinstance(value, bool):
            return value
        return tenant_id is not None and tenant_id in value
```

Register it once in a service provider and resolve it from the container where the decision
is made. Test both flag states in CI.

**Flag lifecycle:** create -> enable for testing -> canary -> full rollout -> remove the flag
and the dead path. A flag without an owner and a removal date becomes permanent debt.

### Staged Rollouts

```
Pull request merged to main
    │
    ▼
  Staging deployment (automatic)
    │  forward migrations applied, /ready green, smoke test of critical flows
    ▼
  Production deployment (manual approval via a protected environment, or automatic after staging)
    │  forward migrations applied, /ready green
    ▼
  Monitor error rate, latency and queue depth (15-minute window minimum)
    │
    ├── Regression detected -> roll back the application (see below)
    └── Clean -> done
```

### Rollback Plan

Every deployment must be reversible — but in Craft, **the database is forward-only**. Rolling
back means redeploying the previous application version against the current schema, never
rewinding the schema. That only works if every schema change was additive and backward
compatible (expand, migrate, contract — see the `deprecation-and-migration` skill,
`.claude/skills/deprecation-and-migration/SKILL.md`). If the previous version cannot run
against the new schema, the migration was unsafe and the fix is to ship a forward correction.

```yaml
# .github/workflows/rollback.yml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      tag:
        description: "Release tag to redeploy, for example v3.20.0-r00013"
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.tag }}
      - name: Redeploy previous application version (schema untouched)
        run: ./deploy/deploy.sh production "${{ inputs.tag }}" --skip-migrations
        env:
          DEPLOY_TOKEN: ${{ secrets.PRODUCTION_DEPLOY_TOKEN }}
      - name: Verify readiness
        run: curl -fsS "${{ vars.PRODUCTION_URL }}/ready"
```

The fastest rollback is still turning off a feature flag; the next fastest is redeploying the
previous image tag.

## Environment Management

```
.env.example        -> committed (template, no real values)
.env                -> NOT committed (local development)
test env file       -> committed only if it holds no real secrets
CI secrets          -> GitHub Secrets, scoped per environment
Production secrets  -> the deployment platform's secret store or a vault
```

- CI never holds production secrets. Use separate, low-privilege credentials for CI.
- The application key is generated per environment (`python dev.py key:generate`), never
  copied between them.
- Protect `production` as a GitHub environment with required reviewers so a production deploy
  is always an explicit approval.
- Test fixtures and seeders use synthetic data only — never a copy of production personal data
  (LGPD/GDPR).

## Automation Beyond CI

### Dependency Updates

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 10

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 10
```

Point `directory` at the folder that holds `pyproject.toml`. Every dependency bump that can
affect behavior still gets a `Changed` entry in `CHANGELOG.md`, and a bump closing a CVE gets
a `Security` entry.

### Pre-Commit Mirrors CI

Run the cheap gates locally with `pre-commit` (ruff, `lint_language.py`, `lint_structure.py`)
so CI failures are rare surprises instead of the first signal. CI stays authoritative: a local
hook can be skipped, the pipeline cannot.

### Build Cop Role

Name someone responsible for keeping the default branch green. When it breaks, the build cop
fixes or reverts immediately — not whoever caused it, whenever they get to it. This stops
broken builds from piling up while everyone assumes someone else is on it.

### Pull Request Checks

- **Required reviews:** at least one approval before merge
- **Required status checks:** every gate job must pass before merge
- **Branch protection:** no force-pushes or direct pushes to the default branch
- **Pull request template:** a checklist for tests, changelog entry, translation keys and migrations
- **Auto-merge:** allowed once all checks pass and the review is approved

## CI Optimization

When the pipeline exceeds ten minutes, apply these in order of impact:

```
Slow pipeline?
├── Cache dependencies
│   └── actions/setup-python with `cache: pip`
├── Run jobs in parallel
│   └── Lint and gates, SQLite tests, PostgreSQL tests as separate jobs
├── Only run what changed
│   └── Path filters: skip the PostgreSQL job for docs-only changes
├── Shard the suite
│   └── Matrix over test directories, or pytest-xdist where tests are isolated
├── Optimize the tests
│   └── Move slow scenarios to a scheduled workflow, keep the critical path fast
└── Bigger runners
    └── Larger hosted or self-hosted runners for CPU-heavy jobs
```

**Example: caching and parallel jobs**

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14", cache: pip }
      - run: pip install -e ".[dev]"
      - run: ruff check .

  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14", cache: pip }
      - run: pip install -e ".[dev]"
      - run: python .claude/rules/lint_language.py --format github
      - run: python .claude/rules/lint_structure.py

  test-sqlite:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14", cache: pip }
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests --cov=app
```

Path filters must never skip the non-regression test when `pyproject.toml`,
`engine/__init__.py` or `CHANGELOG.md` changed.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "CI is too slow" | Optimize it (see CI Optimization). A five-minute pipeline prevents hours of debugging. |
| "This change is trivial, skip CI" | Trivial changes break builds, and CI is fast for them anyway. |
| "The test is flaky, just re-run" | Flaky tests hide real bugs and train people to ignore red. Fix the flakiness. |
| "We'll add CI later" | Projects without CI accumulate broken states. Set it up on day one. |
| "Manual testing is enough" | Manual testing does not scale and is not repeatable. Automate what you can. |
| "SQLite is green, PostgreSQL can wait" | Production runs PostgreSQL. Dialect bugs only surface where the dialect runs. |
| "Just add an exemption to the language gate" | Exemptions are argued case by case for legitimate localized copy, never for convenience. Fix the output. |
| "Use migrate:fresh in CI, it's a throwaway database" | The pipeline then never proves forward migrations work. Those commands are banned everywhere. |
| "We can roll back the migration if the deploy fails" | The schema is forward-only. Make the change backward compatible so the old code still runs. |

## Red Flags

- No CI pipeline, or one that does not run on every pull request and push to the default branch
- CI failures ignored, re-run until green, or marked non-blocking
- Tests skipped, deselected or deleted to make the pipeline pass
- `lint_language.py` or `lint_structure.py` missing from CI, or exemptions added to pass
- Only SQLite in CI for an application that runs PostgreSQL in production
- `migrate:fresh`, `migrate:reset`, `migrate:refresh`, `db:wipe` or `db:drop` anywhere in a workflow
- A release job that tags from `pyproject.toml` alone, ignoring `__release__`
- Production deploys with no staging verification or no approval gate
- No rollback mechanism, or a rollback that depends on reversing migrations
- Secrets inline in workflow files or committed `.env` files
- Long pipelines with no optimization effort

## Verification

After setting up or modifying CI:

- [ ] Gates present: ruff, type check (if enforced), `lint_language.py`, `lint_structure.py`, pytest, non-regression test, dependency audit, image build
- [ ] The suite runs against SQLite and against the production PostgreSQL version
- [ ] Pipeline runs on every pull request and every push to the default branch
- [ ] Failures block merge (branch protection with required status checks)
- [ ] Migrations in CI and deploys are forward-only; no banned destructive command appears
- [ ] Release job verifies version sync, `rNNNNN` format and the changelog heading before tagging `vX.Y.Z-rNNNNN`
- [ ] Secrets live in GitHub Secrets or a vault, never in code or workflow files
- [ ] Deployment has a rollback path that redeploys the previous image without touching the schema
- [ ] CI failures feed back into the development loop with the exact failing output
- [ ] The test stage runs in under ten minutes

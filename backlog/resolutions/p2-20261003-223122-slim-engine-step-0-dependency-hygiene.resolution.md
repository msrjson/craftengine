---
task: p2-20261003-223122-slim-engine-step-0-dependency-hygiene
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T11:53:18Z
finished_at: 2026-10-07T11:59:07Z
---

## What changed

- `data/engine/security/__init__.py`: the five public names (`Captcha`,
  `Firewall`, `FirewallMiddleware`, `HoneypotService`, `PQC`) are now resolved
  lazily with a PEP 562 `__getattr__`/`__dir__` instead of importing every
  submodule at package import.
- `data/engine/http/middleware.py`: the module-level
  `from engine.security.firewall import FirewallMiddleware` became a lazy
  re-export (`__getattr__`) backed by a `TYPE_CHECKING` import so the name stays
  in `__all__` and ruff accepts it. Importing the middleware stack no longer
  loads `engine.security`.
- `data/tests/test_security_lazy_imports.py` (new): asserts through `sys.modules`
  in a subprocess that `import engine`, `import engine.http.middleware` and
  `import engine.security` pull in no security subsystem, and that the deferred
  names remain importable from both modules.
- `data/CHANGELOG.md`: entry under `[Unreleased]`.

The dependency half of step 0 (`fastapi` removed, `faker` moved to the `dev`
extra, `s3 = ["boto3>=1.28.0"]` declared, Pillow import deferred in the captcha)
had already shipped in commit `ad63fb5` / v4.2.0-r00020, a week before this task
was filed; `data/pyproject.toml` needed no change.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -c "import sys, engine; print(sorted(m for m in sys.modules if m.startswith(\"engine.security\")))"'
# []

docker exec framework sh -lc 'cd /app && python -c "import sys; import engine.http.middleware; print(sorted(m for m in sys.modules if m.startswith(\"engine.security\")))"'
# []   (was engine.security.captcha, .firewall, .honeypot, .pqc before the change)

docker exec framework sh -lc 'cd /app && python -c "import sys; import engine.security; print(sorted(m for m in sys.modules if m.startswith(\"engine.security\")))"'
# ['engine.security']   (package only, no subsystem)

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_security_lazy_imports.py -q'
# 5 passed in 1.40s

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 1981 passed, 66 skipped in 109.80s

# full suite, PostgreSQL
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2043 passed, 4 skipped in 126.56s

cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0

cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml
# Language standard: clean.

docker exec framework sh -lc 'cd /app && ruff check engine/security/__init__.py engine/http/middleware.py tests/test_security_lazy_imports.py'
# All checks passed!
```

## Follow-ups

None for the code. `docs/adr/0002-slim-engine-optional-extras.md` still reads
`Status: accepted (owner, 2026-09-25); not yet implemented`, which is now stale
for step 0 (steps 1-6 remain); it was left untouched because the ADR lives at
the workspace root, outside this task's `touches` (which are all under
`data/`).

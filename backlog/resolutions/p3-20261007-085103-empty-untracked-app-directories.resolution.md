---
task: p3-20261007-085103-empty-untracked-app-directories
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T17:46:13Z
finished_at: 2026-10-07T17:48:37Z
---

## What changed

- `data/app/Services/__init__.py` (new, tracked): the documented `app/Services/`
  (README, "Structure") becomes a package like every other application code
  directory, so it is declared in the tree rather than lingering as an untracked
  empty folder.
- Removed `data/app/Services/Identity/` and `data/app/Support/`. Neither held
  source — only an ignored `__pycache__` — and `app/Support/` is documented
  nowhere and referenced by no code (`grep` found no `app.Support` import). The
  decision recorded in the task was taken: declare the documented directory,
  remove the undocumented one.

`data/README.md` needed no edit: it already lists `Services/` in the structure,
and `Support/` was never in it.

## Verification

```bash
git ls-files data/app/Services data/app/Support
# data/app/Services/__init__.py      (Support returns nothing)

ls -d data/app/Support
# ls: cannot access 'data/app/Support': No such file or directory

# no empty untracked directory left under data/app:
for d in $(find data/app -type d ! -name __pycache__); do
  [ -z "$(ls -A "$d")" ] && [ "$(git ls-files "$d" | wc -l)" = 0 ] && echo "EMPTY-UNTRACKED: $d"
done
# (nothing printed)

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2141 passed, 68 skipped in 126.18s

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!
cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml
# Language standard: clean.
```

## Follow-ups

None. `p3-20261004-161342` (landing locale number format) was left unclaimed and
recorded as a board FINDING: its edit would entangle uncommitted user changes in
`data-website/site.json`.

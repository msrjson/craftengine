---
task: p3-20261006-192449-upgrade-config-drift-notice
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:24:58Z
finished_at: 2026-10-07T18:25:15Z
---

## What changed

- `data/engine/lifecycle/changelog.py`: a release may declare the project files
  it wants reviewed with a `Project files:` line in its section (items separated
  by `;`); `sections_between()` parses it into the new `Section.project_files`.
- `data/engine/cli/engine_commands.py`: `_render_move` prints those items under
  "project files to review", after the attention entries — so `engine upgrade`
  and `engine update` show them.
- `data/documentation/engine-lifecycle.md`: documents the convention.
- `data/tests/test_engine_lifecycle.py`: `TestProjectFilesNote` covers a release
  that declares items and one that declares none.
- `data/CHANGELOG.md`: entry — outside the task's `touches`, but the repository's
  CHANGELOG policy requires one for every `engine/` change.

The note is informational only: nothing edits a project file automatically, per
the task's Notes.

## Verification

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_engine_lifecycle.py -q'
# 35 passed in 1.43s

docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2157 passed, 68 skipped in 104.53s

docker exec framework sh -lc 'cd /app && ruff check engine'                 # All checks passed!
cd data && python tools/check_engine_boundary.py                             # ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
python3 .agents/rules/lint_backlog.py && python3 .agents/rules/lint_board.py  # clean
```

## Follow-ups

None. A release opts in by adding the `Project files:` line; the historical
`app/connectors` case keeps its resolution note in its own CHANGELOG entry.

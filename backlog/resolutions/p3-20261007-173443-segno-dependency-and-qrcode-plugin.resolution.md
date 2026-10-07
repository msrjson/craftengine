---
task: p3-20261007-173443-segno-dependency-and-qrcode-plugin
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T18:34:57Z
finished_at: 2026-10-07T18:35:30Z
---

## What changed

- `data/pyproject.toml`: `segno>=1.6` is a runtime dependency — a maintained,
  pure-Python QR encoder, never a hand-rolled matrix.
- `data/plugins/qrcode/` (new): a legacy `PluginManager` plugin exposing `QrCode`
  through the container. `svg()` returns SVG markup, `png()` PNG bytes and
  `data_uri()` a `data:` URI; empty content is refused.
- `data/tests/test_qrcode_plugin.py`: 7 tests (SVG markup, PNG magic, distinct
  content differs, data URI, empty refused, discovery, registration).
- `data/CHANGELOG.md`: entry.

## Verification

```bash
# the image rebuilt from pyproject carries the dependency
docker compose -f data/docker-compose.yml build app
docker compose -f data/docker-compose.yml up -d app
docker exec framework sh -lc 'cd /app && python -c "import segno; print(segno.__version__)"'
# segno 1.6.6

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_qrcode_plugin.py -q'
# 7 passed in 1.05s

docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2165 passed, 68 skipped in 127.58s

cd data && python tools/check_engine_boundary.py          # ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
docker exec framework sh -lc 'cd /app && ruff check engine'   # All checks passed!
```

## Follow-ups

None. The `qrcode` plugin is the QR half of Slice 5's QR/barcode item; `segno`
encodes QR (2D barcodes) only, so no separate 1D symbology ships.

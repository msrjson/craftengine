---
id: "20261007-173443"
title: Add the segno dependency and the QR/barcode official plugin
type: feature
priority: 3
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T17:34:43Z
updated_at: 2026-10-07T18:35:30Z
source: Slice 5 (p2-20261007-124247) QR/barcode item; the dependency is outside its touches
touches:
  - data/pyproject.toml
  - data/plugins/qrcode/
  - data/tests/
  - data/CHANGELOG.md
---

## Problem

Slice 5's QR/barcode item must produce real QR codes with `segno`, but `segno`
is not a dependency and adding it needs `pyproject.toml` (and the image), which
Slice 5's `touches` exclude. The example under
`data/documentation/examples/plugins/qrcode_generator/` only draws a placeholder
matrix, not a scannable code.

## Evidence

- `data/pyproject.toml` has no `segno` (`grep -n segno data/pyproject.toml` is
  empty).
- The `framework` container has no `segno` (`python -c "import segno"` fails
  inside it), so the image also needs a rebuild after the dependency is added.
- Slice 5 (`p2-20261007-124247`) touches exclude `pyproject.toml`.

## Done when

- [ ] `segno` is declared as a runtime dependency in `data/pyproject.toml` and
      available in the `framework` container after a rebuild.
- [ ] An official plugin `data/plugins/qrcode/` (legacy `PluginManager` shape:
      `PLUGIN` dict + `register(app)`) generates a real, scannable QR code (SVG
      and PNG) and a 1D barcode from `segno`.
- [ ] Tests in `data/tests/` cover generation and a known payload round-trip.
- [ ] `data/CHANGELOG.md` entry; ruff, engine-boundary and language gates clean.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -c "import segno; print(segno.__version__)"'
docker exec framework sh -lc 'cd /app && python -m pytest tests/test_qrcode_plugin.py -q'
cd data && python tools/check_engine_boundary.py
```

## Notes

Adding a runtime dependency is a supply-chain change: pick an established,
maintained package (segno is pure Python, MIT). Rebuild the development image so
the container sees it. Reference: `data/documentation/examples/plugins/qrcode_generator/`
(placeholder only — re-implement, do not copy).

## History

- 2026-10-07T17:34:43Z created by qwen@qwen-code (source: Slice 5 QR/barcode item; the dependency sits outside that task's touches)
- 2026-10-07T18:34:57Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T18:35:30Z resolved by qwen@qwen-code (resolutions/p3-20261007-173443-segno-dependency-and-qrcode-plugin.resolution.md): `segno>=1.6` declared in `pyproject.toml`, the `framework` image rebuilt and `segno 1.6.6` imports in the container; the `qrcode` official plugin (SVG/PNG/data URI) with 7 tests; full SQLite 2165 passed/68 skipped; gates clean

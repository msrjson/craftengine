# Failure log — Slice 5, official plugins (p2-20261007-124247)

## What was tried

Every in-scope item of the slice was landed and verified in the framework
container across seven increments, each its own commit:

| Item | Commit |
|---|---|
| hash-chained audit trail (`auth_audit_logs` chain, migration `2026_10_07_000006`) | `7ee3981` |
| `brazil_validator` plugin | `668e14c` |
| `seo` (cookieless) plugin | `c362a7a` |
| `pix` BR Code plugin | `11e540e` |
| `document_seal` plugin | `0a8b9fa` |
| `mtls` channel + `privacy` kit plugins | `3ab35d7` |

Evidence at the last run:

```bash
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2155 passed, 68 skipped

docker exec framework sh -lc 'cd /app && ruff check engine'   # All checks passed!
cd data && python tools/check_engine_boundary.py              # ENGINE_BOUNDARY_NEW_FINDINGS 0
cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml   # clean
```

## Why it cannot be finished as written

Two items of the slice's own Done-when are outside an agent's authority and were
split into dedicated tasks before implementation:

1. **XLSX export, XMLDSig/PKCS#12, e-signature** need the owner's money/legal
   sizing — the task's own Notes say so. Split to `p3-20261007-173442`
   (`autonomous: false`, `blocked_by: owner-decision`).
2. **QR/barcode** needs the `segno` runtime dependency, which lives in
   `data/pyproject.toml`, outside this task's `touches`. Split to
   `p3-20261007-173443`.

The Done-when lists both, so the slice cannot reach a green verification without
the owner; no assumption resolves it. The file was left claiming its broad paths
(`data/plugins/`, `data/engine/`, `data/database/migrations/`, `data/tests/`,
`data/documentation/`, `data/CHANGELOG.md`), which blocks every other eligible
framework task, so it is failed here to release them.

## Reproduction

```bash
git log --oneline 7ee3981..3ab35d7        # the seven increments
grep -n 'XLSX\|PKCS#12\|e-signature\|segno' \
  backlog/pending/p3-20261007-173442-size-money-legal-slice5-artifacts.md \
  backlog/pending/p3-20261007-173443-segno-dependency-and-qrcode-plugin.md
```

## What would unblock it

- The owner records the sizing decision in `p3-20261007-173442` (keep, shrink or
  drop each artifact) and authorises the `segno` dependency (or drops the QR
  item) in `p3-20261007-173443`. With the Done-when reconciled, this task can be
  moved back to `pending/` and closed, or its remaining items kept in those two
  tasks and this task closed as superseded.

## Left behind

Nothing partial: every file is committed and the tree is clean. The two
remaining items live in the two tasks named above.

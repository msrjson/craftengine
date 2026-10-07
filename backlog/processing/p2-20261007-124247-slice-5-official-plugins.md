---
id: "20261007-124247"
title: Implement Slice 5 of the SoftPax upstream roadmap (official plugins)
type: feature
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 1
claimed_by: qwen@qwen-code
created_at: 2026-10-07T12:42:47Z
updated_at: 2026-10-07T17:37:43Z
source: .agents/plans/softpax-upstream-roadmap.md, Slice 5
touches:
  - data/plugins/
  - data/engine/
  - data/database/migrations/
  - data/tests/
  - data/documentation/
  - data/CHANGELOG.md
---

## Problem

Slice 5 of the upstream roadmap ("Official plugins") is not landed: the plugins
it names exist only as blueprints under `data/documentation/examples/`, or not at
all. Registering them as open work here closes the BQ-01 gap (the roadmap's
Slices 5-6 were only in `.agents/plans/` and a handoff, not in the queue).

## Evidence

- `data/plugins/` holds only `.gitkeep` (no official plugin).
- Brazil validator exists only as `data/documentation/examples/plugins/brazil_validator/`
  (alphanumeric CNPJ, 27-state IE rules).
- QR exists only hand-rolled in `data/documentation/examples/plugins/qrcode_generator/`;
  `segno` is not a dependency.
- `data/engine/security/honeypot.py` writes `auth_audit_logs` with no hash chain
  (`previous_hash`/`chain_hash` absent).

## Done when

- [ ] Each item below ships as an official plugin under `data/plugins/` (or the
  engine, where it is not a plugin), with tests in the container:
  Brazil validator (alphanumeric CNPJ, IE for 27 states), PIX BR Code,
  QR/barcode (`segno`), XLSX export, XMLDSig/PKCS#12, mTLS channel, cookieless
  SEO, privacy kit (portability + legal pages), document seal, e-signature,
  hash-chained audit trail.
- [ ] A deactivating plugin leaves the rest serving (extension fault isolation).
- [ ] Full suite green on SQLite and PostgreSQL in the framework container;
  ruff, engine-boundary and language gates clean.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests -q'
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
cd data && python tools/check_engine_boundary.py
```

## Notes

- The reference is `/data/projects/workspaces/softpax` (read-only learning);
  re-implement to Craft standards, never copy verbatim.
- Artifacts that need money/legal decisions (XLSX, PKCS#12, e-signature) should
  be sized with the owner before implementation.
- Related: p2-20261007-122450 (Slice 4) and p2-20261007-124248 (Slice 6).

## History

- 2026-10-07T12:42:47Z created by qwen@qwen-code (source: .agents/plans/softpax-upstream-roadmap.md, Slice 5; queued after the Slice 4 task)
- 2026-10-07T17:18:00Z claimed by qwen@qwen-code (attempt 1)
- 2026-10-07T17:18:00Z scope note by qwen@qwen-code: landing the slice item by item, starting with the hash-chained audit trail (migration on auth_audit_logs + HoneypotService chain), which needs no new dependency and no owner sizing; the money/legal items (XLSX, PKCS#12, e-signature) will be split into an owner-decision task before implementation, per this task's Notes
- 2026-10-07T17:27:49Z progress by qwen@qwen-code (item 2): the brazil_validator official plugin landed under data/plugins/ as a legacy PluginManager plugin (PLUGIN dict + register(app)) - CPF, legacy and 2026-alphanumeric CNPJ, Inscricao Estadual for all 27 states (SINTEGRA), RG, and CEP/phone/CNAE/address normalizers; results carry error_code + message_key only, no user-facing copy; 31 tests, full SQLite 2111 passed/68 skipped, gates clean. Item 1 (hash-chained audit trail) landed earlier at commit 7ee3981
- 2026-10-07T17:31:06Z progress by qwen@qwen-code (item 3): the cookieless SEO plugin landed under data/plugins/seo/ - server-side slugification, canonical URLs, head metadata and a title/body audit, reading and writing no cookie; improvement suggestions are message keys, not copy; 11 tests, full SQLite 2122 passed/68 skipped, ruff/engine-boundary/language gates clean
- 2026-10-07T17:34:10Z progress by qwen@qwen-code (item 4): the PIX BR Code plugin landed under data/plugins/pix/ - Pix.brcode builds a static or dynamic EMV payload (PIX GUI, key, merchant name/city, optional amount and txid, CRC16) and Pix.verify recomputes the checksum of a payload it did not build; 11 tests including the CRC16/CCITT-FALSE check value 0x29B1; full SQLite 2133 passed/68 skipped; gates clean
- 2026-10-07T17:34:43Z scope note by qwen@qwen-code: two items split out per the standard and this task's Notes - the QR/barcode item to p3-20261007-173443 (needs the segno dependency, and pyproject.toml is outside these touches) and the XLSX/PKCS#12/e-signature artifacts to the owner-decision task p3-20261007-173442. Landed so far: item 1 hash-chained audit trail (7ee3981), item 2 brazil_validator (668e14c), item 3 cookieless SEO (c362a7a), item 4 PIX BR Code (11e540e). Still in scope here and not yet landed: mTLS channel, privacy kit (portability + legal pages), document seal
- 2026-10-07T17:37:43Z progress by qwen@qwen-code (item 5): the document seal plugin landed under data/plugins/document_seal/ - DocumentSeal.seal returns a tamper-evident SHA-256 digest (or HMAC when keyed) and verify recomputes it, so any change to the document is detected; 8 tests, full SQLite 2141 passed/68 skipped; gates clean. Still in scope and not yet landed: mTLS channel, privacy kit (portability + legal pages)

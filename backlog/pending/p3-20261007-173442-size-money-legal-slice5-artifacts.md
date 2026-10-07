---
id: "20261007-173442"
title: Size the XLSX export, XMLDSig/PKCS#12 and e-signature artifacts before implementing them
type: decision
priority: 3
autonomous: false
blocked_by: owner-decision
max_attempts: 2
attempts: 0
created_at: 2026-10-07T17:34:42Z
updated_at: 2026-10-07T17:34:42Z
source: Slice 5 (p2-20261007-124247) Notes: money/legal artifacts are sized with the owner
touches: []
---

## Problem

Slice 5 lists three artifacts whose shape is not an engineering call: the XLSX
export, XMLDSig/PKCS#12 and the e-signature. Each carries a money or legal
decision — the spreadsheet contract a counterparty expects, which certificate
store and key protection are acceptable, and who the signature legally binds —
so the slice's own Notes say they are sized with the owner before
implementation. Slice 5 cannot close its Done-when until these are sized or
explicitly dropped.

## Evidence

- `backlog/processing/p2-20261007-124247-slice-5-official-plugins.md`, Notes:
  "Artifacts that need money/legal decisions (XLSX, PKCS#12, e-signature) should
  be sized with the owner before implementation."
- `.agents/plans/softpax-upstream-roadmap.md`, Slice 5, names the three items.
- Reference implementation to re-implement: `/data/projects/workspaces/softpax`
  (read-only learning).

## Done when

- [ ] The owner records a decision in this file for each of the three artifacts:
      keep and implement, replace with a smaller scope, or drop.
- [ ] For each kept artifact, a `feature` task is opened with its `touches` and
      a checkable Done-when; this decision task then closes as `resolved`.
- [ ] Any dropped artifact is recorded so Slice 5's Done-when can be corrected.

## Verify

No command: the outcome is an owner decision recorded in `## History`.

## Notes

Blocked on the owner. Reference implementations live in the softpax workspace;
re-implement to Craft standards, never copy verbatim. Slice 5
(`p2-20261007-124247`) stays open until this decision is made.

## History

- 2026-10-07T17:34:42Z created by qwen@qwen-code (source: Slice 5 Notes; the money/legal artifacts cannot be implemented without the owner's sizing)

---
id: {{ID}}
from: {{FROM}}
to: {{TO}}
status: open
created: {{DATE}}
claimed_by:
parent:
branch: {{BRANCH}}
commit: {{COMMIT}}
phase: build   # define | plan | build | verify | review | ship
touches: []    # paths this work may edit, e.g. [data/app/http/controllers/, data/tests/test_x.py]
kind: validate # to: local only — validate (tests + user journeys, no edits) | edit (disabled by default)
verify: []     # required for to: local — shell commands that must exit 0, e.g. ["python -m pytest -q tests/test_x.py"]
journeys: []   # user-like checks, e.g. [".claude/journeys/login.json"] (see `journey --help`)
model: auto    # local only: auto (qwen3-agent:4b, the only local model)
max_minutes: 30
---

# {{SLUG}}

## Goal
<!-- One or two sentences: the outcome, not the activity. -->

## Current state
<!-- What exists now. What was done in this session. Uncommitted files, if any. -->

## Verified
<!-- Command → result. Anything not proven is marked UNVERIFIED. -->
- `command` → result

## Next steps
<!-- Ordered, concrete, each one verifiable. Name files and functions. -->
1.

## Acceptance criteria
- [ ]

## Constraints and decisions
<!-- Decisions already made (do not re-open), rules that apply, things NOT to touch. -->

## Open questions
<!-- Only questions the receiver cannot answer from the repo. -->

## Context pointers
<!-- Spec/plan/ADR files, relevant skills, links. Paths, not pasted content. -->

## Result
<!-- Filled by the receiver when done: changes, commits, verification output. -->

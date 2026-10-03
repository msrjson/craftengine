---
id: "YYYYMMDD-HHMMSS"
title: <one line>
type: bugfix | feature | chore | decision
priority: 2
autonomous: true
blocked_by: none
max_attempts: 2
attempts: 0
created_at: YYYY-MM-DDTHH:MM:SSZ
updated_at: YYYY-MM-DDTHH:MM:SSZ
source: <audit, incident, commit or document this came from>
touches:
  - data/<path>
---

## Problem

What is wrong or missing, and who it affects.

## Evidence

- `data/<path>:<line>` - what is there.

## Done when

- [ ] A criterion a command or a test can check.

## Verify

```bash
docker exec framework sh -lc 'cd /app && python -m pytest tests/<test_file>.py -q'
```

## Notes

Constraints, rejected approaches, related tasks.

## History

- YYYY-MM-DDTHH:MM:SSZ created by <agent or owner> (source: <where it came from>)

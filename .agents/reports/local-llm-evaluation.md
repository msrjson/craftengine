# Local LLM evaluation — SoftPax upstream roadmap

Tracks how local Ollama models perform as helpers on real roadmap tasks. Every
output is reviewed by the cloud agent before use; nothing is merged unreviewed.

Scoring: **usable** (merged with at most cosmetic edits) · **partial** (structure
reused, logic corrected) · **rejected** (discarded).

| Date | Slice | Task | Model | Verdict | Findings |
|---|---|---|---|---|---|
| 2026-09-15 | 0.1 | Draft pytest module for `client_ip` / `normalize_ip` (8 specified cases, code inline) | qwen3-agent:4b | partial | Good fixture layout and naming. 3 of 8 assertions wrong: expected the middle IP for a 3-entry chain with `hops=1`; both IPv6 tests asserted the wrong value against the input it built. Would have encoded the bug being fixed. |
